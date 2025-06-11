"""
Dropbox API client for file operations
"""

import logging
from pathlib import Path
from typing import List, Dict
import tempfile
from datetime import timezone

import dropbox
from dropbox.exceptions import ApiError, AuthError

from .config import DropboxConfig


class DropboxClient:
    """Handles all Dropbox operations for the voice memo service"""
    
    def __init__(self, config: DropboxConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        try:
            # Initialize client based on available credentials
            if config.app_key and config.app_secret and config.refresh_token:
                # Use OAuth 2.0 with refresh token (recommended)
                self.client = dropbox.Dropbox(
                    app_key=config.app_key,
                    app_secret=config.app_secret,
                    oauth2_refresh_token=config.refresh_token
                )
                self.logger.info("Connected to Dropbox using OAuth 2.0 refresh token")
            elif config.access_token:
                # Use legacy access token
                self.client = dropbox.Dropbox(config.access_token)
                self.logger.warning("Using legacy access token - this will expire. Consider switching to OAuth 2.0")
            else:
                raise ValueError("No valid Dropbox credentials provided")
            
            # Test the connection
            self.client.users_get_current_account()
            self.logger.info("Dropbox connection verified successfully")
            
            # Create required folder structure
            self._create_required_folders()
            
        except AuthError as e:
            raise ValueError(f"Invalid Dropbox credentials: {e}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Dropbox: {e}")
    
    def list_inbox_files(self) -> List[Dict]:
        """List all audio files in the inbox folder"""
        inbox_path = f"{self.config.root_folder}/inbox"
        audio_extensions = {'.wav', '.mp3', '.m4a', '.aac', '.flac', '.opus', '.ogg'}
        
        self.logger.debug(f"Checking inbox path: '{inbox_path}'")
        
        # Debug: Also check what's in the root folder
        try:
            root_result = self.client.files_list_folder(self.config.root_folder)
            self.logger.debug(f"Root folder contents: {[entry.name for entry in root_result.entries]}")
        except Exception as e:
            self.logger.debug(f"Couldn't list root folder: {e}")
        
        try:
            # Try with recursive=True to see if there are any nested files
            result = self.client.files_list_folder(inbox_path, recursive=True)
            files = []
            
            self.logger.debug(f"Found {len(result.entries)} total entries in inbox")
            
            # Debug: Print all entries regardless of type
            for entry in result.entries:
                self.logger.debug(f"Raw entry: {entry.name} | Type: {type(entry).__name__} | Path: {getattr(entry, 'path_display', 'N/A')}")
            
            for entry in result.entries:
                self.logger.debug(f"Found entry: {entry.name} (type: {type(entry).__name__})")
                if isinstance(entry, dropbox.files.FileMetadata):
                    file_ext = Path(entry.name).suffix.lower()
                    self.logger.debug(f"File extension: {file_ext}, checking against: {audio_extensions}")
                    if file_ext in audio_extensions:
                        self.logger.info(f"Adding audio file to processing queue: {entry.name}")
                        # Convert UTC timestamp to local time
                        # Use client_modified (original file date) instead of server_modified (upload date)
                        utc_time = entry.client_modified.replace(tzinfo=timezone.utc)
                        local_time = utc_time.astimezone()
                        
                        files.append({
                            'name': entry.name,
                            'path': entry.path_display,
                            'size': entry.size,
                            'created_time': local_time,
                            'id': entry.id
                        })
                    else:
                        self.logger.debug(f"Skipping non-audio file: {entry.name}")
            
            self.logger.info(f"Found {len(files)} audio files in inbox")
            return files
            
        except ApiError as e:
            # Handle path not found errors
            if 'not_found' in str(e).lower() or 'path_not_found' in str(e).lower():
                self.logger.warning(f"Inbox folder not found: {inbox_path}")
                self.logger.info("Creating required folders...")
                self._create_required_folders()
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
    
    def _create_required_folders(self):
        """Create the required folder structure in Dropbox"""
        folders = [
            f"{self.config.root_folder}/inbox",
            f"{self.config.root_folder}/processing", 
            f"{self.config.root_folder}/failed",
            f"{self.config.root_folder}/processed"
        ]
        
        for folder_path in folders:
            try:
                self.client.files_create_folder_v2(folder_path)
                self.logger.info(f"Created folder: {folder_path}")
            except ApiError as e:
                if 'already_exists' in str(e).lower():
                    self.logger.debug(f"Folder already exists: {folder_path}")
                else:
                    self.logger.warning(f"Failed to create folder {folder_path}: {e}")
                    # Don't raise - some folders might already exist