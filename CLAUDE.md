# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ramble is an automated service that processes voice memos into organized, searchable, and actionable text documents. It monitors a Dropbox inbox folder, transcribes audio files using AssemblyAI, and uses LLMs to process transcripts into structured, topic-separated markdown files.

## Architecture

### Core Workflow

1. **File Ingestion**: Monitor Dropbox `/inbox/` folder for new audio files
2. **Processing Pipeline**: Move files to `/processing/`, generate unique session IDs
3. **Transcription**: Upload to AssemblyAI for speech-to-text
4. **Content Enhancement**: Use cost-effective LLM (GPT-4o-mini/Claude Haiku) for:
   - Content densification (remove filler, repetition)
   - Topic identification and separation
   - Date/time parsing for override detection
5. **Organization**: Create structured output in `/processed/YYYY-MM-DD_HH-MM_[session-title]/`

### Output Structure

Each processed session creates:

- `original_compressed.[ext]` - Compressed audio
- `transcript_raw.md` - Raw AssemblyAI output
- `[topic-title].md` files - Processed content per topic
- `metadata.json` - Processing details and summary

### Implementation Approach

- **Recommended**: Local Python daemon with 60-second polling
- **Alternative**: GitHub Actions (with noted limitations)
- **Key Dependencies**: Dropbox API, AssemblyAI, LLM APIs (Claude/OpenAI), FFmpeg

## Configuration Schema

The service expects a `config.yaml` with:

- Dropbox access token and root folder path
- AssemblyAI API key for transcription
- LLM service configuration (Claude/OpenAI/Google)
- Processing options (audio compression, file size limits)

## Development Notes

- Sequential file processing to avoid API rate limits
- Universal audio format support (.wav, .mp3, .m4a, .aac, etc.)
- Robust error handling with retry logic and failed file quarantine
- Python recommended for MVP due to rich ecosystem for AI/audio tasks
- Consider Go for future production rewrite if performance becomes critical
