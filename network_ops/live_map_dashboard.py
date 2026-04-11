"""
인프라 생존 지도(Live Map) Streamlit 대시보드.
Ping·서비스 포트·원격 읽기 전용 명령 결과를 서버/네트워크 탭으로 표시합니다.

  cd network_ops
  streamlit run live_map_dashboard.py
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_OPS = Path(__file__).resolve().parent
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from live_map.inventory_loader import load_inventory
from live_map.pipeline import run_live_map_scan
from live_map.safety import is_destructive_command
from live_map.infra_prompt import _exec_on_entry, _find_entry


def _default_yaml() -> Path:
    return _OPS / "live_map" / "hosts.yaml"


def _map_x(host_id: str) -> int:
    h = hashlib.md5(host_id.encode("utf-8")).hexdigest()
    return int(h[:6], 16) % 1000


def main() -> None:
    st.set_page_config(page_title="인프라 생존 지도", layout="wide")
    st.title("인프라 생존 지도 (Live Map)")
    st.caption("Ping · 서비스 포트 · WinRM / SSH / Netmiko 읽기 전용 점검 — 동시 접속 최대 10대")

    with st.sidebar:
        st.header("설정")
        default_p = _default_yaml()
        inv_path = st.text_input(
            "hosts.yaml 경로",
            value=str(default_p) if default_p.is_file() else str(_OPS / "live_map" / "hosts.example.yaml"),
            help="실제 운영 시 live_map/hosts.yaml 을 복사해 사용하세요.",
        )
        path = Path(inv_path).expanduser()
        run_btn = st.button("스캔 실행", type="primary")

    if not path.is_file():
        st.error(f"인벤토리 파일이 없습니다: {path}")
        st.info("`live_map/hosts.example.yaml` 을 `hosts.yaml` 로 복사하고 환경 변수에 비밀번호를 설정하세요.")
        return

    try:
        servers, nets = load_inventory(path)
    except Exception as e:
        st.exception(e)
        return

    st.session_state.setdefault("server_rows", [])
    st.session_state.setdefault("network_rows", [])

    if run_btn:
        with st.spinner("병렬 헬스체크 중 (최대 10 동시)…"):
            try:
                s_rows, n_rows = run_live_map_scan(path)
            except Exception as e:
                st.exception(e)
                return
        st.session_state["server_rows"] = s_rows
        st.session_state["network_rows"] = n_rows

    tab_srv, tab_net, tab_danger = st.tabs(["서버", "네트워크", "원격 명령(주의)"])

    with tab_srv:
        rows = st.session_state["server_rows"]
        if not rows:
            st.info('사이드바에서 "스캔 실행"을 누르세요.')
        else:
            df = pd.DataFrame(rows)
            cols = [
                "id",
                "hostname",
                "role",
                "os_type",
                "health_tier",
                "ping",
                "ports_all_open",
                "remote_ok",
                "remote_snippet",
            ]
            display = df[[c for c in cols if c in df.columns]]
            st.dataframe(display, use_container_width=True, hide_index=True)

            plot_df = pd.DataFrame(
                {
                    "map_x": [_map_x(str(r.get("id") or "")) for r in rows],
                    "lane": [1] * len(rows),
                    "host": [r.get("id") for r in rows],
                    "health_tier": [r.get("health_tier") or "down" for r in rows],
                }
            )
            st.subheader("생존 지도(개요)")
            st.scatter_chart(plot_df, x="map_x", y="lane", color="health_tier")

    with tab_net:
        rows = st.session_state["network_rows"]
        if not rows:
            st.info('사이드바에서 "스캔 실행"을 누르세요.')
        else:
            df = pd.DataFrame(rows)
            cols = [
                "id",
                "hostname",
                "role",
                "device_type",
                "health_tier",
                "ping",
                "ports_all_open",
                "remote_ok",
                "remote_snippet",
            ]
            display = df[[c for c in cols if c in df.columns]]
            st.dataframe(display, use_container_width=True, hide_index=True)

            plot_df = pd.DataFrame(
                {
                    "map_x": [_map_x(str(r.get("id") or "")) for r in rows],
                    "lane": [0] * len(rows),
                    "host": [r.get("id") for r in rows],
                    "health_tier": [r.get("health_tier") or "down" for r in rows],
                }
            )
            st.subheader("생존 지도(개요)")
            st.scatter_chart(plot_df, x="map_x", y="lane", color="health_tier")

    with tab_danger:
        st.warning(
            "재부팅·삭제 등 **파괴적 명령**은 확인 문구 + 관리자 PIN 이 모두 맞아야 실행됩니다. "
            "PIN 미설정 시 웹에서는 차단하고 `run_live_map_prompt.py` 의 `exec` 를 사용하세요."
        )
        host_id = st.text_input("호스트 id (프롬프트에서 list 로 확인)")
        cmd = st.text_area("실행할 명령", height=100)
        phrase = st.text_input(
            "확인 문구 (환경변수 LIVE_MAP_DESTRUCTIVE_PHRASE, 기본 CONFIRM_DESTRUCTIVE 와 동일하게 입력)",
            value="",
        )
        pin = st.text_input("관리자 PIN (환경변수 LIVE_MAP_ADMIN_PIN)", type="password")
        go = st.button("명령 실행", type="secondary")

        if go and host_id.strip() and cmd.strip():
            try:
                kind, entry = _find_entry(host_id.strip(), servers, nets)
            except KeyError as e:
                st.error(str(e))
            else:
                c = cmd.strip()
                if is_destructive_command(c):
                    expected = (os.environ.get("LIVE_MAP_DESTRUCTIVE_PHRASE") or "CONFIRM_DESTRUCTIVE").strip()
                    admin_pin = (os.environ.get("LIVE_MAP_ADMIN_PIN") or "").strip()
                    if phrase.strip() != expected:
                        st.error("확인 문구가 일치하지 않습니다.")
                    elif not admin_pin:
                        st.error(
                            "파괴적 명령: LIVE_MAP_ADMIN_PIN 환경 변수를 설정한 뒤 PIN 을 입력하거나, "
                            "터미널에서 run_live_map_prompt.py 를 사용하세요."
                        )
                    elif pin.strip() != admin_pin:
                        st.error("관리자 PIN 이 일치하지 않습니다.")
                    else:
                        ok, msg = _exec_on_entry(kind, entry, c)
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)
                else:
                    ok, msg = _exec_on_entry(kind, entry, c)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)


# streamlit run 시 전체 스크립트가 반복 실행되므로 모듈 최하단에서 진입합니다.
main()
