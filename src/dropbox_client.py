"""
Dropbox API client for file operations
"""

import logging
from pathlib import Path
from typing import List, Dict
import tempfile

import dropbox
from dropbox.exceptions import ApiError, AuthError

from .config import DropboxConfig


class DropboxClient:
    """Handles all Dropbox operations for the voice memo service"""
    
    def __init__(self, config: DropboxConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        try:
            self.client = dropbox.Dropbox(config.access_token)
            # Test the connection
            self.client.users_get_current_account()
            self.logger.info("Connected to Dropbox successfully")
        except AuthError as e:
            raise ValueError(f"Invalid Dropbox access token: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Dropbox: {e}")
    
    def list_inbox_files(self) -> List[Dict]:
        """List all audio files in the inbox folder"""
        inbox_path = f"{self.config.root_folder}/inbox"
        audio_extensions = {'.wav', '.mp3', '.m4a', '.aac', '.flac', '.opus', '.ogg'}
        
        try:
            result = self.client.files_list_folder(inbox_path)
            files = []
            
            for entry in result.entries:
                if isinstance(entry, dropbox.files.FileMetadata):
                    file_ext = Path(entry.name).suffix.lower()
                    if file_ext in audio_extensions:
                        files.append({
                            'name': entry.name,
                            'path': entry.path_display,
                            'size': entry.size,
                            'created_time': entry.server_modified,
                            'id': entry.id
                        })
            
            return files
            
        except ApiError as e:
            if e.error.is_path_not_found():
                self.logger.warning(f"Inbox folder not found: {inbox_path}")
                return []
            raise e
    
    def move_to_processing(self, file_info: Dict) -> str:
        """Move file from inbox to processing folder"""
        processing_path = f"{self.config.root_folder}/processing/{file_info['name']}"
        
        try:
            self.client.files_move_v2(file_info['path'], processing_path)
            self.logger.info(f"Moved {file_info['name']} to processing")
            return processing_path
        except ApiError as e:
            raise Exception(f"Failed to move file to processing: {e}")
    
    def download_file(self, dropbox_path: str, filename: str) -> Path:
        """Download file to temporary local storage"""
        temp_dir = Path(tempfile.gettempdir()) / "ramble"
        temp_dir.mkdir(exist_ok=True)
        
        local_path = temp_dir / filename
        
        try:
            with open(local_path, 'wb') as f:
                metadata, response = self.client.files_download(dropbox_path)
                f.write(response.content)
            
            self.logger.info(f"Downloaded {filename} to {local_path}")
            return local_path
            
        except ApiError as e:
            raise Exception(f"Failed to download file: {e}")
    
    def move_to_failed(self, file_info: Dict):
        """Move file from inbox to failed folder"""
        failed_path = f"{self.config.root_folder}/failed/{file_info['name']}"
        
        try:
            self.client.files_move_v2(file_info['path'], failed_path)
            self.logger.warning(f"Moved {file_info['name']} to failed folder")
        except ApiError as e:
            self.logger.error(f"Failed to move file to failed folder: {e}")
    
    def move_to_failed_from_processing(self, processing_path: str):
        """Move file from processing to failed folder"""
        filename = Path(processing_path).name
        failed_path = f"{self.config.root_folder}/failed/{filename}"
        
        try:
            self.client.files_move_v2(processing_path, failed_path)
            self.logger.warning(f"Moved {filename} from processing to failed")
        except ApiError as e:
            self.logger.error(f"Failed to move file from processing to failed: {e}")
    
    def delete_processing_file(self, processing_path: str):
        """Delete file from processing folder after successful processing"""
        try:
            self.client.files_delete_v2(processing_path)
            filename = Path(processing_path).name
            self.logger.info(f"Deleted processed file: {filename}")
        except ApiError as e:
            self.logger.error(f"Failed to delete processing file: {e}")
    
    def upload_to_processed(self, local_path: Path, remote_path: str):
        """Upload processed file to the processed folder"""
        try:
            with open(local_path, 'rb') as f:
                self.client.files_upload(
                    f.read(),
                    remote_path,
                    mode=dropbox.files.WriteMode.overwrite
                )
            self.logger.info(f"Uploaded to processed: {remote_path}")
        except ApiError as e:
            raise Exception(f"Failed to upload processed file: {e}")