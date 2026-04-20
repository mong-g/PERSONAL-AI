# Use a lightweight Python base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies for libmagic (needed by fbapy/magic)
RUN apt-get update && apt-get install -y \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port 8000 (Koyeb requires a web service to stay alive)
EXPOSE 8000

# Start the bot and a dummy web server
CMD ["python", "main.py"]
