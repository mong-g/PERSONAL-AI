# Use a lightweight Python base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security (Hugging Face requirement)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set working directory to user home
WORKDIR $HOME/app

# Copy requirements and install
# We use --user to install in the user's home directory
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy the rest of the application
COPY --chown=user . .

# Expose port 7860 (Hugging Face default)
EXPOSE 7860

# Start the bot
CMD ["python", "main.py"]
