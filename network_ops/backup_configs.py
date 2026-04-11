import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from netmiko import ConnectHandler

from backup_compare import diff_summary, read_prior_config_text
from ops_logging import get_ops_logger, init_network_ops_logging
from ops_notify import notify_config_backup_changed
from ops_secrets import load_all_secrets, resolve_ssh_password


def read_devices_csv(csv_path: Path) -> List[Dict]:
    """devices.csv에서 장비 접속 정보를 읽습니다. pw는 비워 두고 비밀 파일/터미널로 채울 수 있습니다."""
    devices: List[Dict] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required_columns = {"ip", "id", "pw", "device_type"}
        if not required_columns.issubset(set(reader.fieldnames or [])):
            raise ValueError("devices.csv는 ip,id,pw,device_type 컬럼이 필요합니다.")

        for row in reader:
            ip_address = (row.get("ip") or "").strip()
            user_id = (row.get("id") or "").strip()
            password = (row.get("pw") or "").strip()
            device_type = (row.get("device_type") or "").strip()
            if not (ip_address and user_id and device_type):
                get_ops_logger().warning("행 데이터가 불완전하여 건너뜁니다: %s", row)
                continue
            devices.append(
                {
                    "ip": ip_address,
                    "username": user_id,
                    "password": password,
                    "device_type": device_type,
                }
            )
    return devices


def backup_single_device(
    device: Dict,
    backup_dir: Path,
    log: logging.Logger,
) -> Tuple[Path, str]:
    """한 장비에 SSH 접속해 show run을 백업 파일로 저장합니다. (경로, 설정 텍스트) 반환."""
    device_ip = device["ip"]
    output_file = backup_dir / f"{device_ip}_{device['device_type']}.cfg"
    log.info(
        "SSH 접속 시도 host=%s device_type=%s user=%s target_file=%s",
        device_ip,
        device["device_type"],
        device["username"],
        output_file.name,
    )
    connection = None
    try:
        connection = ConnectHandler(
            host=device_ip,
            username=device["username"],
            password=device["password"],
            device_type=device["device_type"],
            timeout=10,
            conn_timeout=10,
            auth_timeout=10,
            banner_timeout=10,
        )
        log.info("SSH 세션 수립 완료 host=%s", device_ip)
        running_config = connection.send_command("show run", read_timeout=60)
        output_file.write_text(running_config, encoding="utf-8")
        log.info("백업 파일 기록 완료 host=%s bytes=%d", device_ip, len(running_config))
        return output_file, running_config
    except Exception as e:
        log.error("SSH 접속 또는 백업 실패 host=%s: %s", device_ip, e, exc_info=True)
        raise
    finally:
        if connection is not None:
            try:
                connection.disconnect()
                log.info("SSH 연결 종료 host=%s", device_ip)
            except Exception as ex:
                log.warning("SSH disconnect 중 경고 host=%s: %s", device_ip, ex)


def audit_config_text(config_text: str) -> Dict:
    """보안 감사 규칙을 검사합니다."""
    lower_text = config_text.lower()
    has_no_ip_http_server = "no ip http server" in lower_text

    insecure_snmp_lines = []
    for line in config_text.splitlines():
        normalized_line = line.strip().lower()
        if "snmp-server community" in normalized_line and (
            "public" in normalized_line or "private" in normalized_line
        ):
            insecure_snmp_lines.append(line.strip())

    return {
        "no_ip_http_server": has_no_ip_http_server,
        "insecure_snmp_lines": insecure_snmp_lines,
    }


def write_report(report_path: Path, audit_rows: List[Dict]) -> None:
    """감사 결과를 report.txt에 요약합니다."""
    now_text = datetime.now().isoformat(timespec="seconds")
    lines = [f"보안 감사 리포트 ({now_text})", "=" * 60]

    for row in audit_rows:
        lines.append(f"[장비] {row['ip']} ({row['device_type']})")
        lines.append(f"- 백업 파일: {row['backup_file']}")
        lines.append(
            "- 규칙1(no ip http server): "
            + ("PASS" if row["audit"]["no_ip_http_server"] else "FAIL")
        )
        if row["audit"]["insecure_snmp_lines"]:
            lines.append("- 규칙2(snmp community public/private): FAIL")
            for snmp_line in row["audit"]["insecure_snmp_lines"]:
                lines.append(f"  * {snmp_line}")
        else:
            lines.append("- 규칙2(snmp community public/private): PASS")
        lines.append("-" * 60)

    report_path.write_text("\n".join(lines), encoding="utf-8")


def run_backup_and_audit() -> None:
    """CSV 기반 장비 백업 + 보안 감사 + (선택) 설정 변경 알림."""
    base_dir = Path(__file__).resolve().parent
    log = init_network_ops_logging(base_dir)
    secrets = load_all_secrets(base_dir)

    notify_on_change = bool(secrets.get("notify_on_config_change"))

    csv_path = base_dir / "devices.csv"
    if not csv_path.exists():
        log.error("devices.csv를 찾지 못했습니다: %s", csv_path)
        raise FileNotFoundError(f"devices.csv를 찾지 못했습니다: {csv_path}")

    date_dir = datetime.now().strftime("%Y-%m-%d")
    backup_dir = base_dir / "backups" / date_dir
    backup_dir.mkdir(parents=True, exist_ok=True)

    log.info("백업 작업 시작 backups_dir=%s 알림_on_change=%s", backup_dir, notify_on_change)

    devices = read_devices_csv(csv_path)
    log.info("총 %d개 장비를 순차 백업합니다.", len(devices))

    audit_rows = []
    for device in devices:
        ip = device["ip"]
        pw = resolve_ssh_password(ip, device["password"], secrets)
        if not pw:
            log.error("SSH 비밀번호를 확보하지 못해 건너뜀: %s (CSV pw 비우고 secrets.enc 또는 터미널 입력)", ip)
            continue
        device = {**device, "password": pw}

        output_file = backup_dir / f"{ip}_{device['device_type']}.cfg"
        prior_text = read_prior_config_text(base_dir, ip, device["device_type"], output_file)

        try:
            backup_file, new_text = backup_single_device(device, backup_dir, log)
            audit_result = audit_config_text(new_text)
            audit_rows.append(
                {
                    "ip": ip,
                    "device_type": device["device_type"],
                    "backup_file": str(backup_file),
                    "audit": audit_result,
                }
            )
        except Exception:
            continue

        if notify_on_change and prior_text is not None:
            changed, excerpt = diff_summary(prior_text, new_text)
            if changed:
                try:
                    notify_config_backup_changed(
                        secrets,
                        device_ip=ip,
                        device_type=device["device_type"],
                        summary="이전 백업 대비 running-config 내용이 달라졌습니다.",
                        diff_excerpt=excerpt,
                    )
                    log.info("설정 변경 알림 전송 완료 host=%s", ip)
                except Exception as ne:
                    log.error("설정 변경 알림 실패 host=%s: %s", ip, ne, exc_info=True)

    report_path = backup_dir / "report.txt"
    write_report(report_path, audit_rows)
    log.info("감사 리포트 생성 완료: %s", report_path)


if __name__ == "__main__":
    run_backup_and_audit()
