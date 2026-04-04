FROM python:3.11-slim

WORKDIR /app

# Install dependencies (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Verify manifest signature exists — do NOT sign at build time
RUN python -c "from pathlib import Path; assert Path('manifest/security_policy.json.sig').exists(), 'Missing manifest signature — run: python main.py sign-manifest before building'"

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

ENV ALETHEIA_MODE=active
ENV ALETHEIA_LOG_LEVEL=INFO

CMD ["uvicorn", "bridge.fastapi_wrapper:app", "--host", "0.0.0.0", "--port", "8000"]
