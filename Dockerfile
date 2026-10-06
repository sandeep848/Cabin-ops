FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 1001 --create-home cabinops
COPY backend ./backend
COPY scripts ./scripts
RUN mkdir -p /data && chown cabinops:cabinops /data
ENV ENV=production CABINOPS_DB_PATH=/data/cabinops.db
USER cabinops
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3)"
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
