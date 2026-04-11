"""설정 백업 변경 알림 — 메일·텔레그램 (비밀 값은 호출자가 secrets에서만 전달)."""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from typing import Any, Dict, List, Optional

import requests

# 텔레그램 단일 메시지 길이 제한
_TELEGRAM_MAX = 4000


def _smtp_config_ok(smtp: Dict[str, Any]) -> bool:
    return bool(
        (smtp.get("host") or "").strip()
        and (smtp.get("from_addr") or "").strip()
        and (smtp.get("to_addrs") or [])
        and (smtp.get("password") or "").strip()
    )


def send_email_smtp(smtp: Dict[str, Any], subject: str, body: str) -> None:
    """STARTTLS SMTP로 텍스트 메일 발송."""
    if not _smtp_config_ok(smtp):
        raise ValueError("SMTP 설정(host, from_addr, to_addrs, password)이 불완전합니다.")

    host = str(smtp["host"]).strip()
    port = int(smtp.get("port") or 587)
    user = (smtp.get("user") or "").strip()
    password = str(smtp["password"])
    from_addr = str(smtp["from_addr"]).strip()
    to_addrs: List[str] = [str(x).strip() for x in (smtp.get("to_addrs") or []) if str(x).strip()]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        if user:
            server.login(user, password)
        else:
            server.login(from_addr, password)
        server.send_message(msg)


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    """Bot API sendMessage."""
    url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
    chunk = text[:_TELEGRAM_MAX]
    r = requests.post(
        url,
        json={"chat_id": chat_id.strip(), "text": chunk, "disable_web_page_preview": True},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API 오류: {data}")


def notify_config_backup_changed(
    secrets: Dict[str, Any],
    *,
    device_ip: str,
    device_type: str,
    summary: str,
    diff_excerpt: str,
) -> None:
    """
    이전 백업 대비 변경이 있을 때 메일/텔레그램 전송.
    secrets: load_all_secrets 결과(smtp, telegram 키).
    """
    subject = f"[네트워크 백업] 설정 변경 감지 {device_ip} ({device_type})"
    body = f"장비: {device_ip} ({device_type})\n\n{summary}\n\n--- diff 요약 ---\n{diff_excerpt}"

    smtp = secrets.get("smtp") or {}
    tg = secrets.get("telegram") or {}
    bot = (tg.get("bot_token") or "").strip()
    chat_id = (tg.get("chat_id") or "").strip()

    errors: List[str] = []
    ok_any = False
    if _smtp_config_ok(smtp):
        try:
            send_email_smtp(smtp, subject, body)
            ok_any = True
        except Exception as e:
            errors.append(f"SMTP: {e}")
    if bot and chat_id:
        try:
            send_telegram_message(bot, chat_id, f"{subject}\n\n{body}"[:_TELEGRAM_MAX])
            ok_any = True
        except Exception as e:
            errors.append(f"Telegram: {e}")

    if not ok_any:
        if not _smtp_config_ok(smtp) and not (bot and chat_id):
            raise RuntimeError("알림 채널이 설정되지 않았습니다(smtp 또는 telegram).")
        raise RuntimeError("; ".join(errors) if errors else "알림 전송 실패")
