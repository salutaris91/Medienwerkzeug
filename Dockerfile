FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    rclone \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set up environment variables for paths and configuration
ENV MW_RUNTIME=docker
ENV MW_PORT=5001
ENV MW_SETTINGS_FILE=/config/settings.json
ENV MW_JOBS_STATE_FILE=/config/jobs_state.json
ENV MW_ACTION_LOG_FILE=/config/action_log.jsonl
ENV MW_DATA_DIR=/config/data
ENV MW_ENV_FILE=/config/.env
ENV RCLONE_CONFIG=/config/rclone/rclone.conf
ENV TZ=Europe/Berlin

# Create working directory
WORKDIR /app

# Install Python dependencies including yt-dlp
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt yt-dlp

# Copy application source code
COPY . .

# Expose internal port
EXPOSE 5001

# Entrypoint runs the main module
CMD ["python", "-m", "gui.main"]
