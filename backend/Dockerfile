# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies for bcrypt and psycopg
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Expose port (Railway will inject $PORT)
EXPOSE 8000

# Run uvicorn (Railway will inject PORT env var)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
