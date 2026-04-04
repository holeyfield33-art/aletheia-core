FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Sign manifest at build time
RUN python main.py sign-manifest

EXPOSE 8000

ENV ALETHEIA_MODE=active
ENV ALETHEIA_LOG_LEVEL=INFO

CMD ["uvicorn", "bridge.fastapi_wrapper:app", "--host", "0.0.0.0", "--port", "8000"]
