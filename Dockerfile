# Use a lightweight Python base image
FROM python:3.13-slim

# Force a fresh build every time by using a build argument
ARG CACHEBUST=1

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
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- CRITICAL: Nuke old files and copy fresh ---
# We use a subfolder to ensure no old files from root remain
RUN mkdir -p $HOME/app/core $HOME/app/tools
COPY --chown=user core/ $HOME/app/core/
COPY --chown=user tools/ $HOME/app/tools/
COPY --chown=user main.py README.md $HOME/app/

# Expose port 7860 (Hugging Face default)
EXPOSE 7860

# Start the bot
CMD ["python", "main.py"]
