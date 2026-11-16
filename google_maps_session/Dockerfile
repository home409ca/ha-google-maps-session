FROM debian:bookworm-slim
ENV DEBIAN_FRONTEND=noninteractive DISPLAY=:0 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium tigervnc-standalone-server novnc websockify nginx python3 python3-venv \
    ca-certificates fonts-dejavu-core fonts-noto-color-emoji xfonts-base util-linux \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 browser \
    && python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir aiohttp==3.13.2
COPY app /app
COPY bridge /bridge
COPY nginx.conf /etc/nginx/nginx.conf
WORKDIR /app
CMD ["/opt/venv/bin/python", "/app/run.py"]
