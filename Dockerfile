FROM python:3.14-slim

WORKDIR /app

# Install system dependencies for log rotation and backups
RUN apt-get update && apt-get install -y --no-install-recommends \
    logrotate sqlite3 && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies (layer cache) — hash-pinned for supply-chain verification
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

# Copy application
COPY . .

# Verify manifest signature exists — do NOT sign at build time
RUN python -c "from pathlib import Path; assert Path('manifest/security_policy.json.sig').exists(), 'Missing manifest signature — run: python main.py sign-manifest before building'"

# Create non-root user
RUN addgroup --system appgroup && adduser --system --no-create-home --ingroup appgroup appuser
RUN chown -R appuser:appgroup /app
# Restrict data directory permissions
RUN mkdir -p /app/data && chmod 700 /app/data
# Log rotation config
COPY deploy/logrotate.conf /etc/logrotate.d/aletheia
RUN mkdir -p /var/log/aletheia && chown appuser:appgroup /var/log/aletheia
# Backup directory
RUN mkdir -p /backups && chown appuser:appgroup /backups
USER appuser

EXPOSE 8000

ENV ALETHEIA_MODE=active
ENV ALETHEIA_LOG_LEVEL=INFO

HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "bridge.fastapi_wrapper:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "5"]
