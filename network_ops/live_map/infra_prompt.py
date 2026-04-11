#!/usr/bin/env python3
"""
통합 인프라 프롬프트 (Windows WinRM / Linux SSH / Network Netmiko).
프로그램 시작 시 hosts.yaml 을 로드하고, 대화형으로 원격 명령을 실행합니다.

명령:
  help              도움말
  list              서버·네트워크 장비 id 목록
  scan              생존 지도 스캔 한 번 실행(요약 출력)
  exec <id> "<cmd>" 지정 호스트에 명령 실행 (파괴적 명령은 2차 확인)

환경 변수(비밀번호): hosts.yaml 의 *_password_env 이름과 동일하게 설정하세요.
파괴적 명령 2차 확인: LIVE_MAP_DESTRUCTIVE_PHRASE, LIVE_MAP_ADMIN_PIN — safety 모듈 참고.
"""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .inventory_loader import load_inventory
from .pipeline import run_live_map_scan
from .remote_exec import (
    _env_password,
    collect_network_status,
    collect_server_status,
    run_linux_ssh,
    run_netmiko,
    run_windows_winrm,
)
from .safety import admin_two_step_confirm, is_destructive_command


def _find_entry(
    host_id: str,
    servers: List[Dict[str, Any]],
    nets: List[Dict[str, Any]],
) -> Tuple[str, Dict[str, Any]]:
    for row in servers:
        if row.get("id") == host_id:
            return "server", row
    for row in nets:
        if row.get("id") == host_id:
            return "network", row
    raise KeyError(f"알 수 없는 id: {host_id}")


def _exec_on_entry(kind: str, entry: Dict[str, Any], command: str) -> Tuple[bool, str]:
    if kind == "server":
        os_type = (entry.get("os_type") or "").lower()
        if os_type == "linux":
            pw = _env_password(entry.get("ssh_password_env"))
            return run_linux_ssh(
                entry["hostname"],
                port=int(entry.get("ssh_port") or 22),
                username=str(entry.get("ssh_user") or ""),
                password=pw,
                command=command,
            )
        if os_type == "windows":
            pw = _env_password(entry.get("winrm_password_env"))
            return run_windows_winrm(
                entry["hostname"],
                port=int(entry.get("winrm_port") or 5985),
                transport=str(entry.get("winrm_transport") or "ntlm"),
                username=str(entry.get("winrm_user") or ""),
                password=pw,
                command=command,
            )
        return False, f"지원하지 않는 os_type: {os_type}"
    return run_netmiko(
        entry["hostname"],
        device_type=str(entry.get("netmiko_device_type") or "cisco_ios"),
        port=int(entry.get("ssh_port") or 22),
        username=str(entry.get("ssh_user") or ""),
        password=_env_password(entry.get("ssh_password_env")),
        command=command,
    )


def _run_readonly_status(kind: str, entry: Dict[str, Any]) -> Tuple[bool, str]:
    if kind == "server":
        return collect_server_status(entry)
    return collect_network_status(entry)


def repl_loop(inventory_path: Path) -> None:
    servers, nets = load_inventory(inventory_path)
    print(f"[live-map] 인벤토리 로드: 서버 {len(servers)}대, 네트워크 {len(nets)}대 ({inventory_path})")
    print("[live-map] 'help' 입력 시 명령 목록")

    while True:
        try:
            line = input("live-map> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            return

        if not line:
            continue
        if line in ("exit", "quit", "q"):
            print("종료합니다.")
            return
        if line == "help":
            print(__doc__)
            continue
        if line == "list":
            print("--- servers ---")
            for r in servers:
                print(f"  {r['id']:20}  {r['hostname']:16}  {r.get('os_type')}")
            print("--- network_devices ---")
            for r in nets:
                print(f"  {r['id']:20}  {r['hostname']:16}  {r.get('netmiko_device_type')}")
            continue
        if line == "scan":
            s_res, n_res = run_live_map_scan(inventory_path)
            print(f"서버: up={sum(1 for x in s_res if x.get('health_tier')=='up')} / {len(s_res)}")
            print(f"네트워크: up={sum(1 for x in n_res if x.get('health_tier')=='up')} / {len(n_res)}")
            continue

        if line.startswith("exec "):
            try:
                parts = shlex.split(line, posix=True)
            except ValueError as e:
                print(f"파싱 오류: {e}")
                continue
            if len(parts) < 3:
                print('사용법: exec <id> "<명령>"')
                continue
            _, host_id, *cmd_parts = parts
            command = " ".join(cmd_parts)
            try:
                kind, entry = _find_entry(host_id, servers, nets)
            except KeyError as e:
                print(e)
                continue

            if is_destructive_command(command):
                if not admin_two_step_confirm():
                    print("취소되었습니다.")
                    continue

            ok, msg = _exec_on_entry(kind, entry, command)
            print(("OK " if ok else "FAIL ") + msg[:2000])
            continue

        if line.startswith("status "):
            host_id = line.split(maxsplit=1)[1].strip()
            try:
                kind, entry = _find_entry(host_id, servers, nets)
            except KeyError as e:
                print(e)
                continue
            ok, msg = _run_readonly_status(kind, entry)
            print(("OK " if ok else "FAIL ") + msg[:2000])
            continue

        print("알 수 없는 명령입니다. help 를 입력하세요.")


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="인프라 통합 프롬프트 (WinRM/SSH/Netmiko)")
    p.add_argument(
        "-f",
        "--inventory",
        type=Path,
        default=Path(__file__).resolve().parent / "hosts.yaml",
        help="hosts.yaml 경로",
    )
    args = p.parse_args(argv)
    if not args.inventory.is_file():
        print(f"인벤토리 없음: {args.inventory} (hosts.example.yaml 을 복사하세요)", file=sys.stderr)
        return 1
    repl_loop(args.inventory)
    return 0
