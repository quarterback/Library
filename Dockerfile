FROM python:3.12-slim

WORKDIR /app

# System dependencies for PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmupdf-dev \
    libfreetype6-dev \
    libharfbuzz-dev \
    libjpeg62-turbo-dev \
    libopenjp2-7-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY frontend/ frontend/

# Create corpus directory
RUN mkdir -p corpus/pdfs

# Default port (overridable via PORT env var)
ENV PORT=8000
ENV ENVIRONMENT=production

EXPOSE ${PORT}

# Run with uvicorn — single process is fine for most deployments,
# use gunicorn with uvicorn workers if you need multi-process
CMD uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port ${PORT} \
    --proxy-headers \
    --forwarded-allow-ips='*'
