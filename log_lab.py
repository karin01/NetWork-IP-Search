import csv
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List

try:
    from scapy.all import IP, TCP, UDP, rdpcap
except Exception:  # pragma: no cover
    rdpcap = None
    IP = TCP = UDP = None


ERROR_PATTERNS = {
    "timeout": re.compile(r"timeout|timed out|지연|시간 초과", re.IGNORECASE),
    "connection_reset": re.compile(r"reset|rst|연결 끊김", re.IGNORECASE),
    "connection_refused": re.compile(r"refused|거부", re.IGNORECASE),
    "auth_failed": re.compile(r"auth failed|authentication failed|로그인 실패|인증 실패", re.IGNORECASE),
    "http_5xx": re.compile(r"\b5\d{2}\b|server error", re.IGNORECASE),
}


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _match_error_code(text: str) -> str:
    for code_name, pattern in ERROR_PATTERNS.items():
        if pattern.search(text):
            return code_name
    return "normal"


def _build_summary(events: List[Dict]) -> Dict:
    code_counter = Counter(event["code"] for event in events)
    src_counter = Counter(event["src_ip"] for event in events if event["src_ip"] != "-")
    timeline_counter = defaultdict(int)
    for event in events:
        timeline_key = event["timestamp"][:16] if event["timestamp"] != "-" else "unknown"
        timeline_counter[timeline_key] += 1

    return {
        "generated_at": _iso_now(),
        "total_events": len(events),
        "code_counts": dict(code_counter),
        "top_source_ips": src_counter.most_common(10),
        "timeline": dict(sorted(timeline_counter.items())),
    }


def _parse_text_log(file_path: str) -> List[Dict]:
    events: List[Dict] = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as log_file:
        for line_index, line in enumerate(log_file, start=1):
            message = line.strip()
            if not message:
                continue
            code_name = _match_error_code(message)
            events.append(
                {
                    "timestamp": _iso_now(),
                    "src_ip": "-",
                    "dst_ip": "-",
                    "protocol": "text",
                    "code": code_name,
                    "message": message,
                    "line": line_index,
                }
            )
    return events


def _parse_csv_log(file_path: str) -> List[Dict]:
    events: List[Dict] = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as csv_file:
        reader = csv.DictReader(csv_file)
        for row_index, row in enumerate(reader, start=1):
            raw_message = " ".join(str(value) for value in row.values() if value is not None)
            code_name = _match_error_code(raw_message)
            events.append(
                {
                    "timestamp": row.get("timestamp", _iso_now()),
                    "src_ip": row.get("src_ip", row.get("source", "-")),
                    "dst_ip": row.get("dst_ip", row.get("destination", "-")),
                    "protocol": row.get("protocol", "-"),
                    "code": code_name,
                    "message": raw_message[:500],
                    "line": row_index,
                }
            )
    return events


def _parse_pcap(file_path: str) -> List[Dict]:
    if rdpcap is None:
        raise RuntimeError("pcap 분석 환경이 준비되지 않았습니다. scapy 설치를 확인해주세요.")

    events: List[Dict] = []
    packets = rdpcap(file_path)
    for packet_index, packet in enumerate(packets, start=1):
        src_ip = packet[IP].src if IP and packet.haslayer(IP) else "-"
        dst_ip = packet[IP].dst if IP and packet.haslayer(IP) else "-"
        protocol_name = "unknown"
        message = "packet"
        if TCP and packet.haslayer(TCP):
            protocol_name = "TCP"
            flags = packet[TCP].sprintf("%flags%")
            message = f"tcp flags={flags}"
        elif UDP and packet.haslayer(UDP):
            protocol_name = "UDP"
            message = "udp datagram"

        code_name = _match_error_code(message)
        events.append(
            {
                "timestamp": _iso_now(),
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "protocol": protocol_name,
                "code": code_name,
                "message": message,
                "line": packet_index,
            }
        )
    return events


def analyze_log_file(file_path: str, output_directory: str) -> Dict:
    """로그 파일을 AI 분석 친화 포맷으로 가공하고 요약 통계를 반환합니다."""
    _, extension = os.path.splitext(file_path.lower())
    if extension in {".log", ".txt"}:
        events = _parse_text_log(file_path)
    elif extension == ".csv":
        events = _parse_csv_log(file_path)
    elif extension in {".pcap", ".pcapng"}:
        events = _parse_pcap(file_path)
    else:
        raise ValueError(f"지원하지 않는 로그 형식입니다: {extension}")

    os.makedirs(output_directory, exist_ok=True)
    ai_ready_path = os.path.join(output_directory, "ai_ready.jsonl")
    summary_path = os.path.join(output_directory, "summary.json")

    with open(ai_ready_path, "w", encoding="utf-8") as jsonl_file:
        for event in events:
            jsonl_file.write(json.dumps(event, ensure_ascii=False) + "\n")

    summary = _build_summary(events)
    with open(summary_path, "w", encoding="utf-8") as summary_file:
        json.dump(summary, summary_file, ensure_ascii=False, indent=2)

    return {
        "summary": summary,
        "ai_ready_path": ai_ready_path,
        "summary_path": summary_path,
    }
