# Voice Memo Processing Service - Technical Specification

## Overview
An automated service that processes voice memos into organized, searchable, and actionable text documents with minimal friction. Primary use case: Converting rambling voice recordings into information-dense text for further LLM manipulation and project development.

## Core Workflow

### 1. File Ingestion
- **Inbox Location**: Dropbox folder (path to be provided)
- **Supported Formats**: Any audio format (.wav, .mp3, .m4a, .aac, .flac, etc.)
- **File Sources**: 
  - iPhone voice memos via Siri Shortcuts (already configured)
  - DJI wireless mics (via separate helper utility)
  - Manual upload
- **Mobile Integration**: Seamless "record → share → forget" workflow via iOS shortcut

### 2. Processing Pipeline

#### Stage 1: File Detection & Movement
- Background service monitors `/inbox/` folder
- When new file detected:
  - Move to `/processing/` folder
  - Create unique processing session ID
  - Log processing start time

#### Stage 2: Transcription
- Upload file to AssemblyAI
- Retrieve transcription with timestamps
- Handle API errors and retries
- Store raw transcript

#### Stage 3: Content Enhancement & Topic Separation
- Pass transcript to **cost-effective LLM** (GPT-4o-mini, Claude Haiku) for:
  - **Content Densification**: Remove repetition, filler words, tangents
  - **Topic Identification**: Detect distinct topics/themes within recording
  - **Signal Extraction**: Focus on actionable, information-dense content
  - **Date/Time Parsing**: Extract mentioned dates that override file creation date
  - Convert rambling into structured, scannable format

#### Stage 4: Organization & Multi-File Output
- LLM generates:
  - Overall session title for main folder
  - Individual topic titles and content separation
  - Date override detection (if mentioned date differs significantly from file date)
- Create folder: `/processed/YYYY-MM-DD_HH-MM_[session-title]/`
- Save files:
  - `original_compressed.[ext]` - Voice-optimized compressed audio
  - `transcript_raw.md` - Unprocessed AssemblyAI output
  - `[topic-1-title].md` - First topic's processed content
  - `[topic-2-title].md` - Second topic's processed content (if multiple topics)
  - `metadata.json` - Processing details, summary, topic list

## Technical Architecture

### Execution Environment
**Recommended**: Local Python script with daemon process
**Alternative**: GitHub Actions (with limitations noted below)

**Local Script Advantages**: 
- Always-on processing (1-minute polling)
- No timeout limits
- Direct Dropbox API access
- Immediate processing for daily workflow

**GitHub Actions Limitations**:
- 6-hour maximum runtime per job
- Requires scheduled triggers (not continuous monitoring)
- Cold start delays
- More complex for file management

### Core Dependencies
- **Dropbox API**: File monitoring and management
- **AssemblyAI API**: Speech-to-text transcription
- **LLM API**: Claude/OpenAI/Google for text processing
- **Audio Processing**: FFmpeg for compression (optional)

### Configuration Management
```yaml
# config.yaml
dropbox:
  access_token: ${DROPBOX_TOKEN}
  root_folder: "/voicememos"

transcription:
  service: "assemblyai"
  api_key: ${ASSEMBLYAI_KEY}
  
llm:
  service: "claude" # or "openai", "google"
  api_key: ${LLM_API_KEY}
  model: "claude-3-sonnet"

processing:
  compress_audio: true
  compression_quality: "medium"
  max_file_size_mb: 50
```

## Detailed Implementation Specs

### File Processing Logic
1. **Polling Interval**: Check inbox every 60 seconds (thesis workflow friendly)
2. **Sequential Processing**: Handle files one at a time to avoid API rate limits
3. **Universal Audio Support**: Accept any audio format (.wav, .mp3, .m4a, .aac, etc.)
4. **File Validation**: 
   - Verify audio format compatibility
   - Check file size limits
   - Ensure file is completely uploaded (stability check)
5. **Error Handling**:
   - Retry failed transcriptions (3 attempts)
   - Move problematic files to `/failed/` folder
   - Continue processing queue even if one file fails
   - Log all errors with timestamps

### LLM Processing Prompt Template
```
Process this voice memo transcript into separate, actionable topics:

ORIGINAL TRANSCRIPT:
[transcript_text]

FILE_CREATION_DATE: [file_date]

Please:
1. **IDENTIFY TOPICS**: Separate distinct themes/topics within the recording
2. **DENSIFY**: Remove filler words, repetition, tangents for each topic
3. **DATE DETECTION**: If speaker mentions a specific date that differs from file date by >1 day, note it
4. **STRUCTURE**: Make each topic easily scannable and actionable
5. Generate descriptive filenames for each topic (max 40 chars, use hyphens)
6. Create overall session title

Format response as:
SESSION_TITLE: [overall-session-title]
OVERRIDE_DATE: [YYYY-MM-DD or null]
TOPICS: [
  {
    "filename": "topic-1-descriptive-name",
    "content": "Dense, structured content for topic 1"
  },
  {
    "filename": "topic-2-descriptive-name", 
    "content": "Dense, structured content for topic 2"
  }
]
```

### Directory Structure
```
/dropbox-inbox/              # Dropbox folder for new recordings
/processed/                  # Final organized folders
├── 2025-06-09_13-35_voice-memo-service-architecture/
│   ├── original_compressed.opus
│   ├── transcript_raw.md
│   ├── service-architecture-overview.md
│   ├── deployment-considerations.md
│   └── metadata.json
├── 2025-06-09_14-20_project-brainstorm/
│   ├── original_compressed.opus
│   ├── transcript_raw.md
│   ├── core-features.md
│   └── metadata.json
└── failed/                  # Files that couldn't be processed
```

### Metadata Schema
```json
{
  "processing_date": "2025-06-09T13:35:00Z",
  "original_filename": "voice_memo_001.m4a",
  "session_title": "Voice Memo Service Architecture",
  "override_date": null,
  "duration_seconds": 423,
  "original_size_mb": 12.3,
  "compressed_size_mb": 0.6,
  "transcription_service": "assemblyai",
  "llm_service": "gpt-4o-mini",
  "topics": [
    {
      "filename": "service-architecture-overview.md",
      "word_count": 234
    },
    {
      "filename": "deployment-considerations.md", 
      "word_count": 156
    }
  ],
  "processing_time_seconds": 45
}
```

## Programming Language Recommendation

**Python vs Go Analysis:**

### Python (Recommended for MVP)
**Pros:**
- Excellent libraries: `dropbox-api`, `requests`, `openai`, `ffmpeg-python`
- Rapid development and iteration
- Easy JSON/text processing
- Your existing familiarity
- Rich ecosystem for audio/AI tasks

**Cons:**
- Slightly higher memory usage
- Not as performant for concurrent operations

### Go (Future Consideration)
**Pros:**
- Excellent for long-running daemons
- Superior concurrent file processing
- Single binary deployment
- Lower resource usage

**Cons:**
- Steeper learning curve
- Less mature AI/audio libraries
- Slower initial development

**Recommendation**: Start with Python for rapid MVP development. Go would be excellent for a production rewrite if performance becomes an issue, but Python's ecosystem advantages make it ideal for this project's requirements.