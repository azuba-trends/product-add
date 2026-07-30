# Base image lightweight Linux (Debian)
FROM python:3.11-slim

# Install system dependencies, Xvfb (Virtual Display) aur required tools
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    libxi6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome manually via official .deb package
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm ./google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose Flask port
EXPOSE 5000

# Start Xvfb (Virtual Screen) aur Gunicorn server
CMD Xvfb :99 -screen 0 1920x1080x24 & \
    export DISPLAY=:99 && \
    gunicorn -w 1 -b 0.0.0.0:5000 app:app