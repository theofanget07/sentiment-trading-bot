FROM python:3.11-slim

# Version marker to force Railway rebuild
# Build v2.0 - Multi-service deployment with entrypoint.sh

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY backend/requirements.txt /app/backend/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

# CRITICAL: Copy entrypoint BEFORE app code to ensure it's always updated
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh && \
    echo "Entrypoint ready: $(ls -la /app/entrypoint.sh)"

# Copy application code
COPY . /app

# Set Python path to include backend directory
ENV PYTHONPATH=/app/backend:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# Expose port (Railway will override this)
EXPOSE 8080

# Use smart entrypoint that detects SERVICE_TYPE
# This MUST execute entrypoint.sh, not python bot.py
ENTRYPOINT ["/app/entrypoint.sh"]
