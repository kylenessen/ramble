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

1. **Setup**:
   ```bash
   python setup.py
   ```

2. **Configure**:
   Edit `config.yaml` with your API keys:
   - Dropbox access token
   - AssemblyAI API key
   - LLM API key (Claude or OpenAI)

3. **Run**:
   ```bash
   python main.py
   ```

## Configuration

Copy `config.yaml.example` to `config.yaml` and configure:

```yaml
dropbox:
  access_token: "YOUR_DROPBOX_ACCESS_TOKEN"
  root_folder: "/voicememos"

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