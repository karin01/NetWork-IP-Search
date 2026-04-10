import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="사무실 IP 스캔 대시보드", layout="wide")
st.title("사무실 IP 스캔 대시보드")
st.caption("FastAPI 백엔드와 연동해 사용 중 IP를 실시간으로 확인합니다.")

api_base_url = st.text_input("API 주소", "http://127.0.0.1:8000")
cidr_value = st.text_input("스캔 CIDR", "192.168.1.0/24")

st.subheader("네트워크 대역 계산")
if st.button("대역 계산"):
    try:
        calc_response = requests.get(
            f"{api_base_url.rstrip('/')}/subnet/calc",
            params={"cidr": cidr_value},
            timeout=30,
        )
        calc_response.raise_for_status()
        calc_data = calc_response.json()
        calc_df = pd.DataFrame(
            [
                ("CIDR", calc_data.get("cidr")),
                ("네트워크 주소", calc_data.get("network_address")),
                ("브로드캐스트 주소", calc_data.get("broadcast_address")),
                ("서브넷 마스크", calc_data.get("netmask")),
                ("프리픽스", f"/{calc_data.get('prefix_length')}"),
                ("전체 주소 수", calc_data.get("total_addresses")),
                ("사용 가능 호스트 수", calc_data.get("usable_hosts")),
            ],
            columns=["항목", "값"],
        )
        st.table(calc_df)
    except Exception as error:
        st.error(f"대역 계산 실패: {str(error)}")

st.subheader("사용 중 IP 스캔")
if st.button("즉시 스캔"):
    with st.spinner("네트워크 스캔 중입니다..."):
        try:
            response = requests.get(
                f"{api_base_url.rstrip('/')}/scan",
                params={"cidr": cidr_value},
                timeout=180,
            )
            response.raise_for_status()
            payload = response.json()
            device_rows = payload.get("devices", [])

            st.success(f"스캔 완료: {payload.get('cidr')}")
            st.write(f"마지막 스캔 시간: {payload.get('last_scan_time')}")

            table_df = pd.DataFrame(device_rows)
            if table_df.empty:
                st.info("스캔 결과가 없습니다.")
            else:
                def highlight_status(row):
                    background_color = "#8B0000" if row["status"] == "사용 중" else "#006400"
                    return [f"background-color: {background_color}; color: white"] * len(row)

                styled_df = table_df[["ip", "status", "hostname", "color"]].style.apply(
                    highlight_status, axis=1
                )
                st.dataframe(styled_df, use_container_width=True)
        except Exception as error:
            st.error(f"스캔 실패: {str(error)}")
