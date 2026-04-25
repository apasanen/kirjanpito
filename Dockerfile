FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install first (cache optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy git metadata (for version detection)
COPY .git .git

# Copy application
COPY app/ ./app/
COPY templates/ ./templates/
COPY static/ ./static/

# Create directories
RUN mkdir -p data/receipts

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
