FROM python:3.11-slim

# Telegram bot with JSON storage - production ready

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

# Copy application code
COPY backend /app/backend

# Create user_data directory for JSON storage
RUN mkdir -p /app/backend/user_data && \
    chmod 755 /app/backend/user_data

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port for Railway
EXPOSE 8080

# Start bot with uvicorn (FastAPI webhook mode)
CMD ["uvicorn", "backend.bot_webhook:app", "--host", "0.0.0.0", "--port", "8080"]
