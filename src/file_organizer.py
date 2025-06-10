"""
File organization and output structure management
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict

import ffmpeg

from .config import ProcessingConfig


class FileOrganizer:
    """Handles file organization and output structure creation"""
    
    def __init__(self, config: ProcessingConfig, dropbox_client=None):
        self.config = config
        self.dropbox_client = dropbox_client
        self.logger = logging.getLogger(__name__)
        
        # Create local temp directory for processing
        self.output_root = Path("processed")
        self.output_root.mkdir(exist_ok=True)
        
        self.logger.info(f"File organizer initialized with output root: {self.output_root}")
    
    def create_output_folder(self, processed_content: Dict, audio_path: Path, transcript_data: Dict, file_created_time=None):
        """Create organized output folder with all processed files"""
        # Determine session date
        session_date = self._get_session_date(processed_content, file_created_time)
        session_title = processed_content['session_title']
        
        # Create folder name
        folder_name = f"{session_date}_{session_title}"
        folder_name = self._clean_folder_name(folder_name)
        
        output_folder = self.output_root / folder_name
        output_folder.mkdir(exist_ok=True)
        
        self.logger.info(f"Creating output folder: {output_folder}")
        
        try:
            # Save compressed audio
            self._save_compressed_audio(audio_path, output_folder)
            
            # Save raw transcript
            self._save_raw_transcript(transcript_data, output_folder)
            
            # Save processed content file
            self._save_content_file(processed_content, output_folder)
            
            # Save metadata
            self._save_metadata(processed_content, audio_path, transcript_data, output_folder)
            
            # Upload to Dropbox if client is available
            if self.dropbox_client:
                self._upload_folder_to_dropbox(output_folder, folder_name)
            
            self.logger.info(f"Successfully created output folder: {folder_name}")
            
            # Clean up local files after upload
            if self.dropbox_client and output_folder.exists():
                shutil.rmtree(output_folder)
                self.logger.info(f"Cleaned up local files: {folder_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to create output folder: {e}")
            # Clean up partial folder
            if output_folder.exists():
                shutil.rmtree(output_folder)
            raise e
    
    def _get_session_date(self, processed_content: Dict, file_created_time=None) -> str:
        """Get session date from file creation time only"""
        # Use file creation time if available, otherwise current time
        if file_created_time:
            return file_created_time.strftime('%Y-%m-%d_%H-%M')
        else:
            return datetime.now().strftime('%Y-%m-%d_%H-%M')
    
    def _clean_folder_name(self, folder_name: str) -> str:
        """Clean folder name for filesystem compatibility"""
        # Replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            folder_name = folder_name.replace(char, '-')
        
        # Replace spaces with underscores
        folder_name = folder_name.replace(' ', '_')
        
        # Limit length
        if len(folder_name) > 100:
            folder_name = folder_name[:97] + "..."
        
        return folder_name
    
    def _save_compressed_audio(self, audio_path: Path, output_folder: Path):
        """Save compressed version of the original audio"""
        if not self.config.compress_audio:
            # Just copy the original file
            output_path = output_folder / f"original{audio_path.suffix}"
            shutil.copy2(audio_path, output_path)
            return
        
        # Compress audio using ffmpeg
        output_path = output_folder / "original_compressed.opus"
        
        try:
            quality_settings = {
                'low': '64k',
                'medium': '128k',
                'high': '192k'
            }
            
            bitrate = quality_settings.get(self.config.compression_quality, '128k')
            
            (
                ffmpeg
                .input(str(audio_path))
                .output(str(output_path), acodec='libopus', audio_bitrate=bitrate)
                .overwrite_output()
                .run(quiet=True)
            )
            
            self.logger.info(f"Compressed audio saved: {output_path.name}")
            
        except Exception as e:
            self.logger.warning(f"Audio compression failed, copying original: {e}")
            # Fall back to copying original
            output_path = output_folder / f"original{audio_path.suffix}"
            shutil.copy2(audio_path, output_path)
    
    def _save_raw_transcript(self, transcript_data: Dict, output_folder: Path):
        """Save raw transcript as markdown"""
        from .transcription import TranscriptionService
        
        # Create a temporary service instance to format the transcript
        # This is a bit of a hack, but avoids duplicating the formatting logic
        transcript_content = f"""# Raw Transcript

**Duration:** {transcript_data.get('audio_duration', 'Unknown')} ms
**Language:** {transcript_data.get('language_code', 'Unknown')}
**Confidence:** {transcript_data.get('confidence', 'Unknown'):.2f}

## Transcript Text

{transcript_data['text']}
"""
        
        # Add word-level timestamps if available
        if transcript_data.get('words'):
            transcript_content += "\n\n## Word-Level Timestamps\n\n"
            transcript_content += "| Word | Start (ms) | End (ms) | Confidence |\n"
            transcript_content += "|------|------------|----------|------------|\n"
            
            for word in transcript_data['words'][:50]:  # Limit to first 50 words
                transcript_content += f"| {word['text']} | {word['start']} | {word['end']} | {word['confidence']:.2f} |\n"
            
            if len(transcript_data['words']) > 50:
                transcript_content += "| ... | ... | ... | ... |\n"
        
        output_path = output_folder / "transcript_raw.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(transcript_content)
        
        self.logger.info("Raw transcript saved")
    
    def _save_content_file(self, processed_content: Dict, output_folder: Path):
        """Save the processed content as a single markdown file"""
        session_title = processed_content['session_title']
        content = processed_content['content']
        
        # Create filename from session title
        filename = self._clean_filename(f"{session_title}.md")
        
        output_path = output_folder / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.logger.info(f"Content file saved: {filename}")
    
    def _clean_filename(self, filename: str) -> str:
        """Clean filename for filesystem compatibility"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '-')
        
        # Replace spaces with underscores
        filename = filename.replace(' ', '_')
        
        # Limit length (keep .md extension)
        if len(filename) > 50:
            name_part = filename[:-3] if filename.endswith('.md') else filename
            filename = name_part[:47] + '.md'
        
        # Ensure it ends with .md
        if not filename.endswith('.md'):
            filename += '.md'
        
        return filename
    
    def _save_metadata(self, processed_content: Dict, audio_path: Path, transcript_data: Dict, output_folder: Path):
        """Save processing metadata as JSON"""
        try:
            original_size = audio_path.stat().st_size / (1024 * 1024)  # MB
        except:
            original_size = 0
        
        # Check for compressed file size
        compressed_files = list(output_folder.glob("original_compressed.*"))
        compressed_size = 0
        if compressed_files:
            try:
                compressed_size = compressed_files[0].stat().st_size / (1024 * 1024)  # MB
            except:
                compressed_size = 0
        
        metadata = {
            "processing_date": datetime.now().isoformat(),
            "original_filename": audio_path.name,
            "session_title": processed_content['session_title'],
            "duration_seconds": transcript_data.get('audio_duration', 0) / 1000 if transcript_data.get('audio_duration') else 0,
            "original_size_mb": round(original_size, 2),
            "compressed_size_mb": round(compressed_size, 2),
            "transcription_service": "assemblyai",
            "llm_service": "configured_service",  # This could be passed from config
            "content_filename": self._clean_filename(f"{processed_content['session_title']}.md"),
            "word_count": len(processed_content['content'].split())
        }
        
        output_path = output_folder / "metadata.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        self.logger.info("Metadata saved")
    
    def _upload_folder_to_dropbox(self, local_folder: Path, folder_name: str):
        """Upload all files in local folder to Dropbox processed folder"""
        self.logger.info(f"Uploading folder to Dropbox: {folder_name}")
        
        # Upload all files in the folder
        for file_path in local_folder.iterdir():
            if file_path.is_file():
                # Create Dropbox path
                dropbox_path = f"{self.dropbox_client.config.root_folder}/processed/{folder_name}/{file_path.name}"
                
                try:
                    self.dropbox_client.upload_to_processed(file_path, dropbox_path)
                    self.logger.info(f"Uploaded: {file_path.name}")
                except Exception as e:
                    self.logger.error(f"Failed to upload {file_path.name}: {e}")
                    raise e
        
        self.logger.info(f"Successfully uploaded all files for: {folder_name}")