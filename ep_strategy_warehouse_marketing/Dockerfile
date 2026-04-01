# Backend Dockerfile (Python/FastAPI)
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY solution/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY solution/backend/src /app/src
COPY schema /app/schema

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV APP_MODULE=src.main:app

EXPOSE 8000

# Run the application
CMD ["sh", "-c", "python -m src.scripts.init_database && uvicorn src.main:app --host 0.0.0.0 --port 8000"]
