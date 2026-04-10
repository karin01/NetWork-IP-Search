import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List

import yaml

try:
    import paramiko
except Exception:  # pragma: no cover
    paramiko = None


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _parse_natural_language_instruction(instruction_text: str) -> Dict:
    lower_text = instruction_text.lower()
    if "로그" in instruction_text or "log" in lower_text:
        return {
            "action": "collect_log",
            "commands": ["show logging | tail -n 200", "dmesg | tail -n 200"],
            "description": "최근 로그 수집",
        }
    if "설정" in instruction_text or "config" in lower_text:
        return {
            "action": "apply_config",
            "commands": ["show running-config"],
            "description": "설정값 점검/적용 준비",
        }
    return {
        "action": "run_command",
        "commands": ["show version", "show interface status"],
        "description": "기본 상태 점검",
    }


def _run_on_single_device(device: Dict, commands: List[str], dry_run: bool) -> Dict:
    device_ip = device.get("ip", "")
    username = device.get("username", "")
    password = device.get("password", "")

    if dry_run:
        return {
            "device_ip": device_ip,
            "status": "dry_run",
            "output": "\n".join(f"[DRY-RUN] {command}" for command in commands),
            "executed_at": _iso_now(),
        }

    if paramiko is None:
        return {
            "device_ip": device_ip,
            "status": "failed",
            "output": "paramiko 모듈이 없어 실제 SSH 실행이 불가합니다.",
            "executed_at": _iso_now(),
        }

    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh_client.connect(
            hostname=device_ip,
            username=username,
            password=password,
            timeout=5,
            look_for_keys=False,
            allow_agent=False,
        )
        command_outputs = []
        for command in commands:
            _, stdout, stderr = ssh_client.exec_command(command, timeout=10)
            stdout_text = stdout.read().decode("utf-8", errors="ignore")
            stderr_text = stderr.read().decode("utf-8", errors="ignore")
            command_outputs.append(f"$ {command}\n{stdout_text}\n{stderr_text}")

        return {
            "device_ip": device_ip,
            "status": "success",
            "output": "\n".join(command_outputs),
            "executed_at": _iso_now(),
        }
    except Exception as error:
        return {
            "device_ip": device_ip,
            "status": "failed",
            "output": f"실행 실패: {str(error)}",
            "executed_at": _iso_now(),
        }
    finally:
        ssh_client.close()


def run_automation(
    instruction_text: str,
    inventory_path: str,
    output_directory: str,
    dry_run: bool = True,
) -> Dict:
    """자연어 지시를 해석해 다중 장비 자동화 작업을 실행합니다."""
    with open(inventory_path, "r", encoding="utf-8") as inventory_file:
        inventory = yaml.safe_load(inventory_file) or {}

    devices = inventory.get("devices", [])
    if not devices:
        raise ValueError("인벤토리 파일에 devices 목록이 없습니다.")

    parsed_instruction = _parse_natural_language_instruction(instruction_text)
    commands = parsed_instruction["commands"]

    os.makedirs(output_directory, exist_ok=True)
    results = []
    with ThreadPoolExecutor(max_workers=min(16, max(1, len(devices)))) as executor:
        futures = [
            executor.submit(_run_on_single_device, device, commands, dry_run) for device in devices
        ]
        for future in as_completed(futures):
            results.append(future.result())

    report = {
        "generated_at": _iso_now(),
        "instruction": instruction_text,
        "parsed_instruction": parsed_instruction,
        "dry_run": dry_run,
        "results": sorted(results, key=lambda item: item["device_ip"]),
    }

    report_path = os.path.join(output_directory, "run_report.json")
    with open(report_path, "w", encoding="utf-8") as report_file:
        json.dump(report, report_file, ensure_ascii=False, indent=2)

    return {"report": report, "report_path": report_path}
