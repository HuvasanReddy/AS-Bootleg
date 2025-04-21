# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

COPY requirements.txt .

# System deps for wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 libmagic-dev \
    libjpeg-dev zlib1g-dev libpng-dev libtiff-dev \
    libgl1-mesa-glx libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install wheel setuptools
RUN pip install --no-cache-dir -r requirements.txt --verbose

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p uploads/exports uploads/user_templates

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Initialize and run migrations
RUN flask db init && \
    flask db migrate -m "Initial migration" && \
    flask db upgrade

# Expose the port
EXPOSE 8080

# Run the application
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"] 