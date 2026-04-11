"""
평문 YAML(secrets.plain.yaml)을 secrets.enc 로 암호화합니다.
비밀번호는 코드에 넣지 말고, 실행 시 터미널에서만 입력하세요.

  python encrypt_secrets.py secrets.plain.example.yaml secrets.enc
"""

from __future__ import annotations

import argparse
import base64
import getpass
import os
import secrets as py_secrets
import sys
from pathlib import Path

import yaml
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# ops_secrets.py 와 동일 파라미터 유지
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


def main() -> int:
    parser = argparse.ArgumentParser(description="network_ops 비밀 YAML → secrets.enc 암호화")
    parser.add_argument("plain_yaml", type=Path, help="평문 YAML 경로")
    parser.add_argument("out_enc", type=Path, nargs="?", default=Path("secrets.enc"), help="출력 경로")
    args = parser.parse_args()

    if not args.plain_yaml.is_file():
        print(f"파일 없음: {args.plain_yaml}", file=sys.stderr)
        return 1

    raw_yaml = args.plain_yaml.read_text(encoding="utf-8")
    yaml.safe_load(raw_yaml)  # 형식 검증

    fernet_key = (os.environ.get("NETWORK_OPS_FERNET_KEY") or "").strip()
    if fernet_key:
        token = Fernet(fernet_key.encode("ascii")).encrypt(raw_yaml.encode("utf-8"))
        args.out_enc.write_bytes(token)
        print(f"Fernet 키(환경변수)로 암호화 저장: {args.out_enc.resolve()}")
        return 0

    pw = getpass.getpass("새 마스터 비밀번호(복호화 시 동일하게 입력): ")
    pw2 = getpass.getpass("확인: ")
    if pw != pw2:
        print("비밀번호가 일치하지 않습니다.", file=sys.stderr)
        return 1

    salt = py_secrets.token_bytes(_SALT_LEN)
    key = _derive_fernet_key(pw.encode("utf-8"), salt)
    token = Fernet(key).encrypt(raw_yaml.encode("utf-8"))
    args.out_enc.write_bytes(salt + token)
    print(f"저장 완료(salt+PBKDF2): {args.out_enc.resolve()}")
    print("실행 시: 동일 마스터 비밀번호 입력 또는 NETWORK_OPS_MASTER_PASSWORD / NETWORK_OPS_FERNET_KEY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
