"""
선택적 Webhook 알림 (JSON POST).
WHY: 스캔 주기마다 브라우저를 보지 않아도 신규/사라진 장치를 외부로 알릴 수 있습니다.
"""

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict

_logger = logging.getLogger(__name__)


def post_json_webhook(url: str, payload: Dict[str, Any], *, timeout_seconds: float = 6.0) -> bool:
    """JSON 본문 POST. 실패 시 False, 예외는 삼킵니다(WHY: 스캔 본동작을 막지 않음)."""
    if not (url or "").strip():
        return False
    try:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_obj = urllib.request.Request(
            url.strip(),
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urllib.request.urlopen(request_obj, timeout=timeout_seconds) as response:
            _ = response.read()
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError) as error:
        _logger.warning("Webhook 전송 실패: %s", error)
        return False
