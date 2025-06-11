# Ramble - Voice Memo Processing Service

An automated service that processes voice memos into organized, searchable, and actionable text documents with minimal friction.

## Features

- **Automated Processing**: Monitors Dropbox inbox for new audio files
- **Universal Audio Support**: Handles any audio format (.wav, .mp3, .m4a, .aac, .flac, etc.)
- **AI-Powered Transcription**: Uses AssemblyAI for accurate speech-to-text
- **Content Enhancement**: LLM processing for topic separation and content densification
- **Organized Output**: Creates structured folders with processed topics, metadata, and compressed audio
- **Robust Error Handling**: Retry logic and circuit breakers for reliable operation

## Quick Start

### Local Development

1. **Dependencies**: Install Python dependencies with `pip install -r requirements.txt`
2. **Dropbox OAuth Setup**: 
   - Create a Dropbox app at https://www.dropbox.com/developers/apps
   - For local development: `python setup_oauth.py --app-key YOUR_APP_KEY --app-secret YOUR_APP_SECRET`
3. **Configuration**: Copy `config.yaml.example` to `config.yaml` and add your credentials
4. **Run**: Execute `python main.py` to start the service

### Remote Server Deployment (SSH-only)

For servers without browser access:

1. **Get OAuth URL**: Run on server:
   ```bash
   python setup_oauth_headless.py --app-key YOUR_APP_KEY --app-secret YOUR_APP_SECRET
   ```

2. **Authorize in Browser**: Visit the provided URL on your local machine, authorize the app

3. **Complete Setup**: Copy the authorization code and run on server:
   ```bash
   python setup_oauth_headless.py --app-key YOUR_APP_KEY --app-secret YOUR_APP_SECRET --auth-code YOUR_CODE
   ```

4. **Configure**: Add the credentials to your `config.yaml` or set environment variables

### Environment Variables

For production deployments, use environment variables instead of storing credentials in files:

```bash
export DROPBOX_APP_KEY="your_app_key"
export DROPBOX_APP_SECRET="your_app_secret"
export DROPBOX_REFRESH_TOKEN="your_refresh_token"
export ASSEMBLYAI_API_KEY="your_assemblyai_key"
export OPENROUTER_API_KEY="your_openrouter_key"
```

## Configuration

Copy `config.yaml.example` to `config.yaml` and configure:

```yaml
dropbox:
  # OAuth 2.0 configuration (recommended for long-term use)
  app_key: "${DROPBOX_APP_KEY}"
  app_secret: "${DROPBOX_APP_SECRET}"
  refresh_token: "${DROPBOX_REFRESH_TOKEN}"
  root_folder: "/ramble"

transcription:
  service: "assemblyai"
  api_key: "YOUR_ASSEMBLYAI_API_KEY"
  
llm:
  service: "claude"  # or "openai"
  api_key: "YOUR_LLM_API_KEY"
  model: "claude-3-haiku-20240307"

processing:
  compress_audio: true
  compression_quality: "medium"
  max_file_size_mb: 50
  polling_interval: 60
```

## Directory Structure

```
/dropbox-root-folder/
├── inbox/           # Drop new voice memos here
├── processing/      # Temporary processing location
└── failed/          # Files that couldn't be processed

/local-processed/
├── 2025-06-09_13-35_project-brainstorm/
│   ├── original_compressed.opus
│   ├── transcript_raw.md
│   ├── core-features.md
│   ├── implementation-plan.md
│   └── metadata.json
```

## Requirements

- Python 3.8+
- FFmpeg (for audio compression)
- Internet connection for API services

## API Keys Required

- **Dropbox**: Create an app at https://www.dropbox.com/developers
- **AssemblyAI**: Get API key at https://www.assemblyai.com/
- **Claude**: Get API key at https://console.anthropic.com/
- **OpenAI**: Get API key at https://platform.openai.com/

## Mobile Integration

Use Siri Shortcuts or similar tools to record and upload voice memos directly to the Dropbox inbox folder for seamless "record → share → forget" workflow.