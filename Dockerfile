FROM python:3.11-slim

# Telegram bot with automatic database initialization
# Database init is now handled in bot_webhook.py startup event

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

# Copy application code
COPY backend /app/backend

# Set environment
ENV PYTHONPATH=/app:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Launch bot with uvicorn (DB init happens in bot_webhook.py @app.on_event('startup'))
CMD ["python", "-m", "uvicorn", "backend.bot_webhook:app", "--host", "0.0.0.0", "--port", "8080"]
