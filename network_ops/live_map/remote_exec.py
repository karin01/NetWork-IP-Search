"""Linux SSH, Windows WinRM, Netmiko 원격 읽기 전용 실행."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

import paramiko

try:
    from winrm.protocol import Protocol as WinrmProtocol  # type: ignore
except ImportError:
    WinrmProtocol = None

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException


def _env_password(env_name: Optional[str]) -> str:
    if not env_name:
        return ""
    return (os.environ.get(str(env_name).strip()) or "").strip()


def run_linux_ssh(
    hostname: str,
    *,
    port: int = 22,
    username: str,
    password: str,
    command: str,
    timeout: int = 15,
) -> Tuple[bool, str]:
    """SSH exec 한 줄 명령. (비밀번호는 호출 전에 환경에서 채운 값만 전달)"""
    if not password:
        return False, "SSH 비밀번호 없음(환경 변수 미설정)"
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname,
            port=int(port),
            username=username,
            password=password,
            timeout=timeout,
            allow_agent=False,
            look_for_keys=False,
        )
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        client.close()
        msg = out if out else err
        return True, msg[:4000] if msg else "(출력 없음)"
    except Exception as e:
        try:
            client.close()
        except Exception:
            pass
        return False, str(e)


def run_windows_winrm(
    hostname: str,
    *,
    port: int = 5985,
    transport: str = "ntlm",
    username: str,
    password: str,
    command: str,
    timeout: int = 30,
) -> Tuple[bool, str]:
    """WinRM(WS-Man)으로 cmd 실행 — pywinrm Protocol 사용."""
    if WinrmProtocol is None:
        return False, "pywinrm 미설치 (pip install pywinrm)"
    if not password:
        return False, "WinRM 비밀번호 없음(환경 변수 미설정)"
    scheme = "https" if int(port) == 5986 else "http"
    endpoint = f"{scheme}://{hostname}:{int(port)}/wsman"
    proto = None
    shell_id = None
    command_id = None
    try:
        proto = WinrmProtocol(
            endpoint,
            transport=transport,
            username=username,
            password=password,
            server_cert_validation="ignore",
        )
        shell_id = proto.open_shell()
        command_id = proto.run_command(shell_id, command)
        std_out, std_err, status_code = proto.get_command_output(shell_id, command_id)

        def _to_str(chunk: object) -> str:
            if chunk is None:
                return ""
            if isinstance(chunk, bytes):
                return chunk.decode("utf-8", errors="replace")
            return str(chunk)

        out = _to_str(std_out).strip()
        err = _to_str(std_err).strip()
        text = out or err or f"(exit {status_code})"
        ok = status_code == 0 or bool(out)
        return ok, text[:4000]
    except Exception as e:
        return False, str(e)
    finally:
        if proto is not None and shell_id is not None and command_id is not None:
            try:
                proto.cleanup_command(shell_id, command_id)
                proto.close_shell(shell_id)
            except Exception:
                pass


def run_netmiko(
    hostname: str,
    *,
    device_type: str,
    port: int = 22,
    username: str,
    password: str,
    command: str,
    timeout: int = 30,
) -> Tuple[bool, str]:
    """네트워크 장비 SSH (Netmiko)."""
    if not password:
        return False, "SSH 비밀번호 없음(환경 변수 미설정)"
    dev: Dict[str, Any] = {
        "device_type": device_type,
        "host": hostname,
        "username": username,
        "password": password,
        "port": int(port),
        "timeout": timeout,
        "conn_timeout": timeout,
    }
    conn = None
    try:
        conn = ConnectHandler(**dev)
        out = conn.send_command_timing(command, read_timeout=timeout)
        return True, (out or "").strip()[:4000]
    except (NetmikoAuthenticationException, NetmikoTimeoutException) as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)
    finally:
        if conn is not None:
            try:
                conn.disconnect()
            except Exception:
                pass


def collect_server_status(entry: Dict[str, Any]) -> Tuple[bool, str]:
    """인벤토리 server 행으로 읽기 전용 status_command 실행."""
    cmd = (entry.get("status_command") or "echo ok").strip()
    os_type = (entry.get("os_type") or "").lower()
    host = entry["hostname"]

    if os_type == "linux":
        pw = _env_password(entry.get("ssh_password_env"))
        return run_linux_ssh(
            host,
            port=int(entry.get("ssh_port") or 22),
            username=str(entry.get("ssh_user") or ""),
            password=pw,
            command=cmd,
        )

    if os_type == "windows":
        pw = _env_password(entry.get("winrm_password_env"))
        return run_windows_winrm(
            host,
            port=int(entry.get("winrm_port") or 5985),
            transport=str(entry.get("winrm_transport") or "ntlm"),
            username=str(entry.get("winrm_user") or ""),
            password=pw,
            command=cmd,
        )

    return False, f"알 수 없는 os_type: {os_type}"


def collect_network_status(entry: Dict[str, Any]) -> Tuple[bool, str]:
    """인벤토리 network_devices 행."""
    cmd = (entry.get("status_command") or "show version").strip()
    pw = _env_password(entry.get("ssh_password_env"))
    return run_netmiko(
        entry["hostname"],
        device_type=str(entry.get("netmiko_device_type") or "cisco_ios"),
        port=int(entry.get("ssh_port") or 22),
        username=str(entry.get("ssh_user") or ""),
        password=pw,
        command=cmd,
    )
