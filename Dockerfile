FROM python:3.11-slim

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY main.py .
COPY config.yaml.example .

# Create necessary directories
RUN mkdir -p processed logs

# Create entrypoint script
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD pgrep -f "python.*main.py" || exit 1

# Run as non-root user for security
RUN useradd -m -u 1000 ramble && \
    chown -R ramble:ramble /app
USER ramble

# Expose any needed ports (none needed for this service)
# EXPOSE 8080

# Set entrypoint
ENTRYPOINT ["./entrypoint.sh"]