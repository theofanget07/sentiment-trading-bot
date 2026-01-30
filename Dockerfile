FROM python:3.11-slim

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

# Copy application code
COPY . /app

# Copy and make entrypoint executable
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set Python path to include backend directory
ENV PYTHONPATH=/app/backend:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# Expose port (Railway will override this)
EXPOSE 8080

# Use smart entrypoint that detects SERVICE_TYPE
ENTRYPOINT ["/app/entrypoint.sh"]
