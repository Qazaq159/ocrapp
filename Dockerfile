FROM python:3.8-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Build wheels
COPY webapp/requirements.txt /tmp/
RUN pip wheel --no-cache-dir --wheel-dir=/tmp/wheels -r /tmp/requirements.txt

# Final stage
FROM python:3.8-slim

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-rus \
    tesseract-ocr-kaz \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy wheels and install
COPY --from=builder /tmp/wheels /tmp/wheels
RUN pip install --no-cache --find-links=/tmp/wheels /tmp/wheels/* \
    && rm -rf /tmp/wheels

WORKDIR /app

# Copy app files
COPY webapp /app/

# Pre-create directories and collect static files
RUN mkdir -p media/documents staticfiles \
    && python manage.py collectstatic --noinput

EXPOSE 8000

# Create startup script that runs migrations then starts server
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]