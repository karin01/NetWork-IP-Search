# NetWork-IP Search — Linux 컨테이너 (참고)
# WHY: Windows 전용(netsh, Npcap 등)은 컨테이너에서 기대하지 마세요. docs/guide/cloud-deploy.md 참고.

FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8500
ENV NETWORK_IP_SEARCH_PORT=8500
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
