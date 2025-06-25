#!/bin/bash
set -e

# Function to create config if it doesn't exist
create_config_if_needed() {
    # Check if config.yaml is mounted as read-only volume
    if [ -f /app/config.yaml ] && [ ! -w /app/config.yaml ]; then
        echo "Using mounted config.yaml (read-only)"
        return 0
    fi
    
    # Check if config.yaml exists as a directory (mount issue)
    if [ -d /app/config.yaml ]; then
        echo "WARNING: config.yaml is mounted as directory, creating config from environment variables in /tmp"
        CONFIG_PATH="/tmp/config.yaml"
    else
        CONFIG_PATH="/app/config.yaml"
    fi
    
    if [ ! -f "$CONFIG_PATH" ]; then
        echo "Creating config.yaml from environment variables..."
        cp /app/config.yaml.example "$CONFIG_PATH"
        
        # Replace placeholder values with environment variables
        sed -i "s/\${DROPBOX_APP_KEY}/$DROPBOX_APP_KEY/g" "$CONFIG_PATH"
        sed -i "s/\${DROPBOX_APP_SECRET}/$DROPBOX_APP_SECRET/g" "$CONFIG_PATH"
        sed -i "s/\${DROPBOX_REFRESH_TOKEN}/$DROPBOX_REFRESH_TOKEN/g" "$CONFIG_PATH"
        sed -i "s/\${ASSEMBLYAI_API_KEY}/$ASSEMBLYAI_API_KEY/g" "$CONFIG_PATH"
        sed -i "s/\${OPENROUTER_API_KEY}/$OPENROUTER_API_KEY/g" "$CONFIG_PATH"
        
        # Optional environment variable overrides
        if [ ! -z "$RAMBLE_POLLING_INTERVAL" ]; then
            sed -i "s/polling_interval: 60/polling_interval: $RAMBLE_POLLING_INTERVAL/g" "$CONFIG_PATH"
        fi
        
        if [ ! -z "$RAMBLE_MAX_FILE_SIZE_MB" ]; then
            sed -i "s/max_file_size_mb: 50/max_file_size_mb: $RAMBLE_MAX_FILE_SIZE_MB/g" "$CONFIG_PATH"
        fi
        
        # If we had to create config in /tmp, export the path
        if [ "$CONFIG_PATH" = "/tmp/config.yaml" ]; then
            export RAMBLE_CONFIG_PATH="$CONFIG_PATH"
        fi
        
        echo "Config created successfully at $CONFIG_PATH"
    else
        echo "Using existing config.yaml"
    fi
}

# Function to validate environment variables
validate_env() {
    local missing_vars=()
    
    # Check required environment variables
    [ -z "$DROPBOX_APP_KEY" ] && missing_vars+=("DROPBOX_APP_KEY")
    [ -z "$DROPBOX_APP_SECRET" ] && missing_vars+=("DROPBOX_APP_SECRET")
    [ -z "$DROPBOX_REFRESH_TOKEN" ] && missing_vars+=("DROPBOX_REFRESH_TOKEN")
    [ -z "$ASSEMBLYAI_API_KEY" ] && missing_vars+=("ASSEMBLYAI_API_KEY")
    [ -z "$OPENROUTER_API_KEY" ] && missing_vars+=("OPENROUTER_API_KEY")
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        echo "ERROR: Missing required environment variables:"
        printf '%s\n' "${missing_vars[@]}"
        echo ""
        echo "Please set these environment variables in your docker-compose.yml or Portainer configuration."
        exit 1
    fi
}

# Function to ensure directories exist
ensure_directories() {
    mkdir -p /app/processed /app/logs
    echo "Directories created/verified"
}

# Main execution
echo "Starting Ramble Voice Memo Processing Service..."
echo "=============================================="

# Validate environment
validate_env

# Ensure directories exist
ensure_directories

# Create config if needed
create_config_if_needed

# Set log level if specified
if [ ! -z "$RAMBLE_LOG_LEVEL" ]; then
    if [ "$RAMBLE_LOG_LEVEL" = "DEBUG" ]; then
        LOG_FLAG="--debug"
    else
        LOG_FLAG=""
    fi
else
    LOG_FLAG=""
fi

echo "Starting main process..."
exec python main.py $LOG_FLAG