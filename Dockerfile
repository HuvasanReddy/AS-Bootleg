# Use a slim Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker caching
COPY requirements.txt .

# Install system-level dependencies needed for Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libmagic1 libmagic-dev \
    libjpeg-dev zlib1g-dev libpng-dev libtiff-dev \
    libgl1-mesa-glx libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python build tools
RUN pip install --upgrade pip
RUN pip install wheel setuptools

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt --verbose

# Copy the application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads/exports uploads/user_templates

# Expose port for the app
EXPOSE 8080

# Command to run the application
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"] 