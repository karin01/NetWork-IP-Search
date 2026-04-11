"""
네트워크 백업·알림용 비밀 정보 로드.
WHY: 비밀번호·토큰을 소스에 넣지 않고, 환경 변수 / 암호화 파일 / 터미널 입력으로만 받습니다.
"""

from __future__ import annotations

import base64
import getpass
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# PBKDF2 반복 횟수 (2020년대 권장 수준)
_KDF_ITERATIONS = 390_000
_SALT_LEN = 16


def _derive_fernet_key(password: bytes, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_KDF_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(password))


def _decrypt_secrets_blob(blob: bytes, password: Optional[str], fernet_key_b64: Optional[str]) -> str:
    """salt(16)+cipher 또는 순수 Fernet 토큰."""
    if fernet_key_b64:
        f = Fernet(fernet_key_b64.strip().encode("ascii"))
        return f.decrypt(blob).decode("utf-8")

    if not password:
        if sys.stdin.isatty():
            password = getpass.getpass("암호화 비밀 파일 복호화용 마스터 비밀번호: ")
        else:
            raise RuntimeError(
                "비대화식 실행입니다. NETWORK_OPS_FERNET_KEY 또는 NETWORK_OPS_MASTER_PASSWORD 를 설정하세요."
            )

    if len(blob) >= _SALT_LEN + 32:
        salt, token = blob[:_SALT_LEN], blob[_SALT_LEN:]
        key = _derive_fernet_key(password.encode("utf-8"), salt)
        try:
            return Fernet(key).decrypt(token).decode("utf-8")
        except InvalidToken as e:
            raise RuntimeError("비밀 파일 복호화 실패(비밀번호·파일 형식 확인).") from e

    raise ValueError("secrets.enc 형식이 올바르지 않습니다(최소 길이 부족).")


def load_encrypted_secrets_file(enc_path: Path) -> Dict[str, Any]:
    """NETWORK_OPS_FERNET_KEY 또는 마스터 비밀번호로 secrets.enc 복호화."""
    if not enc_path.is_file():
        return {}
    blob = enc_path.read_bytes()
    fernet_key = (os.environ.get("NETWORK_OPS_FERNET_KEY") or "").strip()
    master_pw = (os.environ.get("NETWORK_OPS_MASTER_PASSWORD") or "").strip() or None
    raw = _decrypt_secrets_blob(blob, master_pw, fernet_key or None)
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        return {}
    return data


def _env_str(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def merge_env_overrides(data: Dict[str, Any]) -> Dict[str, Any]:
    """환경 변수가 있으면 YAML 내용을 덮어씁니다."""
    out = dict(data)

    if _env_str("NETWORK_OPS_SMTP_HOST"):
        smtp = dict(out.get("smtp") or {})
        smtp["host"] = _env_str("NETWORK_OPS_SMTP_HOST")
        if _env_str("NETWORK_OPS_SMTP_PORT"):
            smtp["port"] = int(_env_str("NETWORK_OPS_SMTP_PORT"))
        if _env_str("NETWORK_OPS_SMTP_USER"):
            smtp["user"] = _env_str("NETWORK_OPS_SMTP_USER")
        if _env_str("NETWORK_OPS_SMTP_PASSWORD"):
            smtp["password"] = _env_str("NETWORK_OPS_SMTP_PASSWORD")
        if _env_str("NETWORK_OPS_SMTP_FROM"):
            smtp["from_addr"] = _env_str("NETWORK_OPS_SMTP_FROM")
        if _env_str("NETWORK_OPS_SMTP_TO"):
            addrs = [a.strip() for a in _env_str("NETWORK_OPS_SMTP_TO").split(",") if a.strip()]
            if addrs:
                smtp["to_addrs"] = addrs
        out["smtp"] = smtp

    if _env_str("NETWORK_OPS_TELEGRAM_BOT_TOKEN"):
        tg = dict(out.get("telegram") or {})
        tg["bot_token"] = _env_str("NETWORK_OPS_TELEGRAM_BOT_TOKEN")
        if _env_str("NETWORK_OPS_TELEGRAM_CHAT_ID"):
            tg["chat_id"] = _env_str("NETWORK_OPS_TELEGRAM_CHAT_ID")
        out["telegram"] = tg

    if _env_str("NETWORK_OPS_NOTIFY_ON_CHANGE"):
        v = _env_str("NETWORK_OPS_NOTIFY_ON_CHANGE").lower()
        out["notify_on_config_change"] = v in ("1", "true", "yes", "on")

    return out


def load_all_secrets(base_dir: Path) -> Dict[str, Any]:
    """secrets.enc(선택) + 환경 변수 병합."""
    enc_path = resolve_secrets_enc_path(base_dir)
    merged: Dict[str, Any] = {}
    if enc_path.is_file():
        merged = load_encrypted_secrets_file(enc_path)
    return merge_env_overrides(merged)


def resolve_secrets_enc_path(base_dir: Path) -> Path:
    """NETWORK_OPS_SECRETS_ENC(상대 시 network_ops 기준) 또는 기본 secrets.enc."""
    raw = _env_str("NETWORK_OPS_SECRETS_ENC")
    if not raw:
        return base_dir / "secrets.enc"
    p = Path(raw)
    return p if p.is_absolute() else (base_dir / p)


def device_password_map(secrets: Dict[str, Any]) -> Dict[str, str]:
    raw = secrets.get("device_passwords") or {}
    if not isinstance(raw, dict):
        return {}
    return {str(k).strip(): str(v) for k, v in raw.items() if str(k).strip() and v is not None}


def resolve_ssh_password(ip: str, csv_password: str, secrets: Dict[str, Any]) -> str:
    """CSV pw → 암호화 파일 device_passwords → 터미널 순."""
    p = (csv_password or "").strip()
    if p:
        return p
    dm = device_password_map(secrets)
    got = (dm.get(ip) or "").strip()
    if got:
        return got
    if sys.stdin.isatty():
        return getpass.getpass(f"[{ip}] SSH 비밀번호 (CSV·비밀파일에 없음): ")
    return ""
