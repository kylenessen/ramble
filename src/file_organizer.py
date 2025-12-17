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

    MAX_SESSION_TITLE_CHARS = 40
    
    def __init__(self, config: ProcessingConfig, dropbox_client=None, llm_service=None):
        self.config = config
        self.dropbox_client = dropbox_client
        self.llm_service = llm_service or 'unknown'
        self.logger = logging.getLogger(__name__)
        
        # Create local temp directory for processing
        self.output_root = Path("processed")
        self.output_root.mkdir(exist_ok=True)
        
        self.logger.info(f"File organizer initialized with output root: {self.output_root}")
    
    def create_output_folder(self, processed_content: Dict, audio_path: Path, transcript_data: Dict, file_created_time=None):
        """Create organized output folder with all processed files"""
        # Determine session date
        session_date = self._get_session_date(processed_content, file_created_time)
        session_title = self._truncate_title(
            processed_content.get('session_title', 'Untitled'),
            max_chars=self.MAX_SESSION_TITLE_CHARS,
        )
        
        # Create folder name
        folder_name = f"{session_date}_{session_title}"
        folder_name = self._clean_folder_name(folder_name)
        folder_name = self._ensure_unique_folder_name(folder_name)
        
        output_folder = self.output_root / folder_name
        output_folder.mkdir(exist_ok=False)
        
        self.logger.info(f"Creating output folder: {output_folder}")
        
        try:
            # Save compressed audio
            saved_audio_path = self._save_compressed_audio(audio_path, output_folder, session_title)

            # Save combined content (summary + transcript)
            content_filename = self._save_combined_content_file(
                processed_content,
                transcript_data,
                output_folder,
                folder_name,
                session_title,
            )
            
            # Save metadata
            self._save_metadata(
                processed_content,
                audio_path,
                transcript_data,
                output_folder,
                content_filename=content_filename,
                saved_audio_path=saved_audio_path,
                session_title=session_title,
            )
            
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
            return file_created_time.strftime('%Y-%m-%d')
        else:
            return datetime.now().strftime('%Y-%m-%d')

    def _clean_folder_name(self, folder_name: str) -> str:
        """Clean folder name for filesystem compatibility"""
        # Replace invalid characters
        invalid_chars = '<>:"/\\|?*&'
        for char in invalid_chars:
            folder_name = folder_name.replace(char, '-')
        
        # Replace spaces with underscores
        folder_name = folder_name.replace(' ', '_')
        
        # Limit length
        if len(folder_name) > 100:
            folder_name = folder_name[:97] + "..."
        
        return folder_name

    def _ensure_unique_folder_name(self, folder_name: str) -> str:
        """Ensure output folder name is unique under output root."""
        if not (self.output_root / folder_name).exists():
            return folder_name

        counter = 2
        while True:
            suffix = f"_{counter}"
            max_base_len = 100 - len(suffix)
            base = folder_name[:max_base_len] if len(folder_name) > max_base_len else folder_name
            candidate = f"{base}{suffix}"
            if not (self.output_root / candidate).exists():
                return candidate
            counter += 1

    def _truncate_title(self, title: str, max_chars: int) -> str:
        """Truncate a human-readable title to a short length."""
        title = " ".join((title or "").strip().split())
        if len(title) <= max_chars:
            return title
        if max_chars <= 3:
            return title[:max_chars]
        return title[: max_chars - 3].rstrip() + "..."
    
    def _save_compressed_audio(self, audio_path: Path, output_folder: Path, session_title: str = None):
        """Save compressed version of the original audio"""
        # Create filename from session title if available
        if session_title:
            audio_filename = self._clean_filename(f"{session_title}.m4a" if self.config.compress_audio else f"{session_title}{audio_path.suffix}")
        else:
            audio_filename = "original_compressed.m4a" if self.config.compress_audio else f"original{audio_path.suffix}"
        
        if not self.config.compress_audio:
            # Just copy the original file
            output_path = output_folder / audio_filename
            shutil.copy2(audio_path, output_path)
            return output_path
        
        # Compress audio using ffmpeg
        output_path = output_folder / audio_filename
        
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
                .output(str(output_path), acodec='aac', audio_bitrate=bitrate)
                .overwrite_output()
                .run(quiet=True)
            )
            
            self.logger.info(f"Compressed audio saved: {output_path.name}")
            return output_path
            
        except Exception as e:
            self.logger.warning(f"Audio compression failed, copying original: {e}")
            # Fall back to copying original
            output_path = output_folder / f"original{audio_path.suffix}"
            shutil.copy2(audio_path, output_path)
            return output_path
    
    def _save_combined_content_file(
        self,
        processed_content: Dict,
        transcript_data: Dict,
        output_folder: Path,
        folder_name: str,
        session_title: str,
    ) -> str:
        """Save the summary and transcript into a single markdown file."""
        summary = (processed_content.get("content") or "").strip()
        transcript_text = (transcript_data.get("text") or "").strip()

        summary = self._strip_leading_h1(summary)

        combined = "\n".join(
            [
                f"# {session_title}".rstrip(),
                "",
                summary,
                "",
                "## Transcript",
                "",
                transcript_text,
                "",
            ]
        )

        filename = self._clean_filename(f"{folder_name}.md")
        output_path = output_folder / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(combined)

        self.logger.info(f"Combined content file saved: {filename}")
        return filename

    def _strip_leading_h1(self, markdown: str) -> str:
        """Remove a leading single H1 line from markdown (common in LLM output)."""
        if not markdown:
            return markdown

        lines = markdown.splitlines()
        idx = 0
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
        if idx < len(lines) and lines[idx].startswith("# "):
            idx += 1
            if idx < len(lines) and not lines[idx].strip():
                idx += 1
        return "\n".join(lines[idx:]).strip()
    
    def _clean_filename(self, filename: str) -> str:
        """Clean filename for filesystem compatibility"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*&'
        for char in invalid_chars:
            filename = filename.replace(char, '-')
        
        # Replace spaces with underscores
        filename = filename.replace(' ', '_')
        
        # Get file extension
        extension = Path(filename).suffix
        name_part = filename[:-len(extension)] if extension else filename
        
        # Limit length (preserve extension)
        if len(name_part) > 80:
            name_part = name_part[:77] + "..."
        
        return name_part + extension
    
    def _save_metadata(
        self,
        processed_content: Dict,
        audio_path: Path,
        transcript_data: Dict,
        output_folder: Path,
        *,
        content_filename: str,
        saved_audio_path: Path,
        session_title: str,
    ):
        """Save processing metadata as JSON"""
        try:
            original_size = audio_path.stat().st_size / (1024 * 1024)  # MB
        except:
            original_size = 0
        
        compressed_size = 0
        try:
            if saved_audio_path and saved_audio_path.exists():
                compressed_size = saved_audio_path.stat().st_size / (1024 * 1024)  # MB
        except:
            compressed_size = 0
        
        metadata = {
            "processing_date": datetime.now().isoformat(),
            "original_filename": audio_path.name,
            "session_title": session_title,
            "duration_seconds": transcript_data.get('audio_duration', 0) / 1000 if transcript_data.get('audio_duration') else 0,
            "original_size_mb": round(original_size, 2),
            "compressed_size_mb": round(compressed_size, 2),
            "transcription_service": "assemblyai",
            "llm_service": self.llm_service,
            "content_filename": content_filename,
            "word_count": len((processed_content.get("content") or "").split()),
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
