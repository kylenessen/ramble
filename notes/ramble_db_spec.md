# Ramble Database Integration Specification

## Project Context
The ramble project currently processes voice memos through AssemblyAI and an LLM, saving outputs as markdown files to the local filesystem. We need to modify it to also save summaries to a PostgreSQL database for integration with n8n workflows.

## Current Architecture
- Voice memos are uploaded to Dropbox inbox
- Python service processes them using AssemblyAI for transcription
- LLM processes transcripts into organized summaries with topics
- Results are saved as markdown files locally
- **New requirement**: Also save all data to PostgreSQL database

## Database Connection Details

### PostgreSQL Configuration
```yaml
host: localhost  # or use environment variable DB_HOST
port: 5432       # or use environment variable DB_PORT
database: ramble
user: ramble_user
password: <from environment variable DB_PASSWORD>
```

### Environment Variables to Add
```bash
DB_HOST=localhost
DB_PORT=5432
DB_PASSWORD=your_secure_password_here
```

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS voice_summaries (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    audio_filename VARCHAR(255),
    transcript_raw TEXT,
    summary_processed TEXT,
    topics JSONB,
    tasks JSONB,
    metadata JSONB,
    processing_status VARCHAR(50) DEFAULT 'completed',
    dropbox_path VARCHAR(500)
);

-- Indexes for performance
CREATE INDEX idx_summary_search ON voice_summaries 
    USING gin(to_tsvector('english', summary_processed));
CREATE INDEX idx_topics ON voice_summaries USING gin(topics);
CREATE INDEX idx_tasks ON voice_summaries USING gin(tasks);
CREATE INDEX idx_created_at ON voice_summaries(created_at DESC);
```

## Required Code Changes

### 1. Add Database Dependencies
Add to `requirements.txt`:
```
psycopg2-binary==2.9.9
```

### 2. Create Database Module
Create a new file `database.py`:

```python
import psycopg2
from psycopg2.extras import Json
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseStorage:
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        """Establish database connection with retry logic"""
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database='ramble',
                user='ramble_user',
                password=os.getenv('DB_PASSWORD')
            )
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def save_summary(self, 
                     audio_filename: str,
                     transcript_raw: str,
                     summary_processed: str,
                     topics: List[Dict[str, str]],
                     tasks: List[Dict[str, Any]],
                     metadata: Dict[str, Any],
                     dropbox_path: Optional[str] = None) -> int:
        """
        Save processed voice memo data to database
        
        Args:
            audio_filename: Original audio file name
            transcript_raw: Raw transcription from AssemblyAI
            summary_processed: Processed summary from LLM
            topics: List of extracted topics with their content
            tasks: List of extracted tasks (if any)
            metadata: Additional metadata (processing time, model used, etc.)
            dropbox_path: Path in Dropbox where files are stored
            
        Returns:
            ID of inserted record
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO voice_summaries 
                    (audio_filename, transcript_raw, summary_processed, 
                     topics, tasks, metadata, dropbox_path)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    audio_filename,
                    transcript_raw,
                    summary_processed,
                    Json(topics),
                    Json(tasks) if tasks else Json([]),
                    Json(metadata),
                    dropbox_path
                ))
                self.conn.commit()
                record_id = cur.fetchone()[0]
                logger.info(f"Saved summary to database with ID: {record_id}")
                return record_id
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to save to database: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
```

### 3. Extract Tasks from Summary
Create a task extraction function to identify actionable items:

```python
def extract_tasks_from_summary(summary_text: str, topics: List[Dict]) -> List[Dict[str, Any]]:
    """
    Extract potential tasks from the summary and topics
    
    Look for patterns like:
    - Action items
    - TODO mentions
    - "Need to", "Should", "Must", "Will" phrases
    - Deadlines or time-sensitive items
    """
    tasks = []
    
    # This is a simple implementation - enhance based on your LLM output format
    # You might want to use regex or another LLM call to extract tasks
    
    task_indicators = [
        'todo:', 'task:', 'action item:', 'need to', 'should', 
        'must', 'will', 'deadline:', 'by', 'follow up'
    ]
    
    # Check summary and all topics for task indicators
    all_text = summary_text + '\n'.join([t.get('content', '') for t in topics])
    
    lines = all_text.lower().split('\n')
    for line in lines:
        if any(indicator in line for indicator in task_indicators):
            tasks.append({
                'text': line.strip(),
                'extracted_at': datetime.now().isoformat(),
                'source': 'auto-extracted'
            })
    
    return tasks
```

### 4. Modify Main Processing Function
Update your main processing function to include database storage:

```python
from database import DatabaseStorage
import traceback

# Initialize database connection
db_storage = DatabaseStorage()

def process_audio_file(audio_file_path: str, dropbox_path: str):
    """Main processing function - modify your existing function"""
    
    try:
        # ... existing transcription code ...
        transcript_raw = transcribe_audio(audio_file_path)
        
        # ... existing LLM processing code ...
        summary_processed, topics = process_with_llm(transcript_raw)
        
        # NEW: Extract tasks from the summary
        tasks = extract_tasks_from_summary(summary_processed, topics)
        
        # ... existing file saving code (keep this for backward compatibility) ...
        save_markdown_files(summary_processed, topics)
        
        # NEW: Save to database
        metadata = {
            'processing_timestamp': datetime.now().isoformat(),
            'llm_model': config.get('llm', {}).get('model'),
            'transcription_service': 'assemblyai',
            'audio_duration_seconds': get_audio_duration(audio_file_path),
            'original_file_size_mb': os.path.getsize(audio_file_path) / (1024 * 1024)
        }
        
        record_id = db_storage.save_summary(
            audio_filename=os.path.basename(audio_file_path),
            transcript_raw=transcript_raw,
            summary_processed=summary_processed,
            topics=topics,
            tasks=tasks,
            metadata=metadata,
            dropbox_path=dropbox_path
        )
        
        logger.info(f"Successfully processed and saved to DB: {audio_file_path}")
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        logger.error(traceback.format_exc())
        # Don't let database errors stop file processing
        # Continue with existing file-based workflow
```

### 5. Update Configuration
Add database configuration to `config.yaml.example`:

```yaml
# Existing configuration...

database:
  enabled: true
  host: "${DB_HOST}"
  port: "${DB_PORT}"
  password: "${DB_PASSWORD}"
```

### 6. Graceful Shutdown
Ensure database connection is closed properly:

```python
# In your main.py or wherever the main loop is
import atexit

# Register cleanup function
atexit.register(lambda: db_storage.close())

# Or in your main function
try:
    # Main processing loop
    run_processing_loop()
finally:
    db_storage.close()
```

## Testing Instructions

1. **Test Database Connection**:
```python
# Create a test script test_db.py
from database import DatabaseStorage

db = DatabaseStorage()
print("Connection successful!")
db.close()
```

2. **Test Data Insertion**:
```python
# Test with sample data
test_id = db.save_summary(
    audio_filename="test_audio.mp3",
    transcript_raw="This is a test transcript",
    summary_processed="Test summary",
    topics=[{"title": "Test Topic", "content": "Test content"}],
    tasks=[{"text": "Test task", "priority": "medium"}],
    metadata={"test": True},
    dropbox_path="/ramble/processed/test"
)
print(f"Inserted record with ID: {test_id}")
```

3. **Verify Data in Database**:
```sql
-- Connect to database and run:
SELECT id, audio_filename, created_at, 
       jsonb_array_length(topics) as topic_count,
       jsonb_array_length(tasks) as task_count
FROM voice_summaries
ORDER BY created_at DESC
LIMIT 5;
```

## Error Handling Considerations

1. **Database Connection Failures**: The code should continue to work with file-based storage if the database is unavailable
2. **Transaction Management**: Each save operation should be atomic
3. **Logging**: All database operations should be logged for debugging
4. **Retries**: Consider implementing retry logic for transient connection issues

## Optional Enhancements

1. **Connection Pooling**: For better performance with multiple concurrent operations
2. **Async Operations**: Use asyncpg for non-blocking database operations
3. **Migration System**: Use Alembic or similar for schema version management
4. **Task Queue**: Consider using Celery for processing if volume increases

## n8n Integration Notes

Once this is implemented, n8n can:
- Poll the `voice_summaries` table for new entries
- Extract tasks from the `tasks` JSONB column
- Mark tasks as processed by updating the metadata
- Query summaries by topics or date ranges

Example n8n query:
```sql
SELECT id, tasks, summary_processed 
FROM voice_summaries 
WHERE tasks != '[]'::jsonb
  AND (metadata->>'tasks_synced_to_todoist') IS NULL
ORDER BY created_at DESC;
```

## Success Criteria

1. ✅ All processed voice memos are saved to the database
2. ✅ Existing file-based workflow continues to work
3. ✅ Database storage doesn't block processing on failure
4. ✅ Tasks are automatically extracted and stored
5. ✅ All data is queryable by n8n workflows