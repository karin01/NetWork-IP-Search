import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from netmiko import ConnectHandler


LOGGER = logging.getLogger("network_backup")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"


def setup_logging(log_file_path: Path) -> None:
    """파일/콘솔 로그를 동시에 설정합니다."""
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_file_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )


def read_devices_csv(csv_path: Path) -> List[Dict]:
    """devices.csv에서 장비 접속 정보를 읽습니다."""
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
            if not (ip_address and user_id and password and device_type):
                LOGGER.warning("행 데이터가 불완전하여 건너뜁니다: %s", row)
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


def backup_single_device(device: Dict, backup_dir: Path) -> Path:
    """한 장비에 SSH 접속해 show run을 백업 파일로 저장합니다."""
    device_ip = device["ip"]
    output_file = backup_dir / f"{device_ip}_{device['device_type']}.cfg"
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
    try:
        running_config = connection.send_command("show run", read_timeout=60)
        output_file.write_text(running_config, encoding="utf-8")
        return output_file
    finally:
        connection.disconnect()


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
    """CSV 기반 장비 백업 + 보안 감사 전체 프로세스."""
    base_dir = Path(__file__).resolve().parent
    csv_path = base_dir / "devices.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"devices.csv를 찾지 못했습니다: {csv_path}")

    date_dir = datetime.now().strftime("%Y-%m-%d")
    backup_dir = base_dir / "backups" / date_dir
    backup_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = backup_dir / "backup_errors.log"
    setup_logging(log_file_path)

    devices = read_devices_csv(csv_path)
    LOGGER.info("총 %d개 장비를 순차 백업합니다.", len(devices))

    audit_rows = []
    for device in devices:
        try:
            backup_file = backup_single_device(device, backup_dir)
            audit_result = audit_config_text(backup_file.read_text(encoding="utf-8", errors="ignore"))
            audit_rows.append(
                {
                    "ip": device["ip"],
                    "device_type": device["device_type"],
                    "backup_file": str(backup_file),
                    "audit": audit_result,
                }
            )
            LOGGER.info("백업 완료: %s", device["ip"])
        except Exception as error:  # WHY: 한 장비 실패가 전체 프로세스를 멈추지 않게 합니다.
            LOGGER.error("백업 실패(%s): %s", device["ip"], str(error))
            continue

    report_path = backup_dir / "report.txt"
    write_report(report_path, audit_rows)
    LOGGER.info("감사 리포트 생성 완료: %s", report_path)


if __name__ == "__main__":
    run_backup_and_audit()
