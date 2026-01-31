FROM python:3.11-slim

# Telegram bot with automatic database initialization

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

# Copy application code
COPY backend /app/backend
COPY scripts /app/scripts

# Make startup script executable
RUN chmod +x /app/scripts/start.sh

# Set environment
ENV PYTHONPATH=/app:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Run startup script (DB init + bot)
CMD ["/app/scripts/start.sh"]
