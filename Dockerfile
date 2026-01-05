# Multi-stage build for Polymarket Trading Bot

FROM python:3.11-slim as base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

FROM base as development

RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    ruff \
    mypy \
    ipython

COPY . .

ENV PYTHONPATH=/app/src
ENV ENVIRONMENT=development

CMD ["python", "-m", "polymarket_bot.main"]

FROM base as production

COPY src/ /app/src/
COPY config/ /app/config/

RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app && \
    mkdir -p /app/logs /app/data && \
    chown -R botuser:botuser /app/logs /app/data

USER botuser

ENV PYTHONPATH=/app/src
ENV ENVIRONMENT=production
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "polymarket_bot.main"]
