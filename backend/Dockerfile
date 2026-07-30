FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend /app
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir -e .

CMD ["sh", "-lc", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level ${UVICORN_LOG_LEVEL:-info} --access-log"]
