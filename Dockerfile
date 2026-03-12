FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

LABEL org.opencontainers.image.source="https://github.com/bavariaande/npm-sync"
LABEL org.opencontainers.image.description="Declarative Nginx Proxy Manager synchronization tool using a YAML hosts inventory."
LABEL org.opencontainers.image.licenses="MIT"

USER appuser

ENTRYPOINT ["python"]
CMD ["-m", "npm_sync", "--config", "/config/hosts.yml"]
