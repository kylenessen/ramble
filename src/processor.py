"""
Main voice memo processing logic
"""

import logging
from pathlib import Path
from typing import List

from .config import Config
from .dropbox_client import DropboxClient
from .transcription import TranscriptionService
from .llm_processor import LLMProcessor
from .file_organizer import FileOrganizer
from .error_handler import ErrorHandler, CircuitBreaker, retry_on_failure


class VoiceMemoProcessor:
    """Main processor that orchestrates the voice memo processing pipeline"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.dropbox = DropboxClient(config.dropbox)
        self.transcription = TranscriptionService(config.transcription)
        self.llm = LLMProcessor(config.llm)
        self.organizer = FileOrganizer(config.processing, self.dropbox)
        
        # Error handling
        self.error_handler = ErrorHandler(max_retries=3, base_delay=2.0)
        self.transcription_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=300)
        self.llm_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=180)
    
    def process_inbox(self):
        """Process all files in the inbox folder"""
        try:
            files = self.dropbox.list_inbox_files()
            
            if not files:
                return
            
            self.logger.info(f"Found {len(files)} files to process")
            
            for file_info in files:
                try:
                    self._process_single_file(file_info)
                except Exception as e:
                    self.logger.error(f"Failed to process {file_info['name']}: {e}")
                    self.dropbox.move_to_failed(file_info)
                    
        except Exception as e:
            self.logger.error(f"Error checking inbox: {e}")
    
    def _process_single_file(self, file_info: dict):
        """Process a single voice memo file through the complete pipeline"""
        filename = file_info['name']
        self.logger.info(f"Processing: {filename}")
        
        # Move to processing folder
        processing_path = self.dropbox.move_to_processing(file_info)
        
        try:
            # Download file for processing
            local_path = self.dropbox.download_file(processing_path, filename)
            
            # Transcribe audio with circuit breaker and retry
            transcript = self.transcription_breaker.call(
                self.error_handler.retry_with_backoff,
                self.transcription.transcribe,
                local_path,
                max_retries=3
            )
            
            # Process with LLM with circuit breaker and retry
            processed_content = self.llm_breaker.call(
                self.error_handler.retry_with_backoff,
                self.llm.process_transcript,
                transcript,
                file_info.get('created_time'),
                max_retries=2
            )
            
            # Organize and save output
            self.organizer.create_output_folder(
                processed_content,
                local_path,
                transcript,
                file_info.get('created_time')
            )
            
            # Clean up
            self.dropbox.delete_processing_file(processing_path)
            local_path.unlink()
            
            self.logger.info(f"Successfully processed: {filename}")
            
        except Exception as e:
            # Move back to failed if processing fails
            self.dropbox.move_to_failed_from_processing(processing_path)
            raise e