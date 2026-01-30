FROM python:3.11-slim

# Simple single-service bot deployment

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

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Launch bot directly with uvicorn
CMD ["python", "-m", "uvicorn", "backend.bot_webhook:app", "--host", "0.0.0.0", "--port", "8080"]
