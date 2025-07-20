"""
Configuration management for Ramble service
"""

import os
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class DropboxConfig:
    root_folder: str
    # OAuth 2.0 fields
    app_key: Optional[str] = None
    app_secret: Optional[str] = None
    refresh_token: Optional[str] = None
    # Legacy token field
    access_token: Optional[str] = None
    
    def __post_init__(self):
        """Validate that either OAuth or legacy token is provided"""
        oauth_provided = all([self.app_key, self.app_secret, self.refresh_token])
        legacy_provided = self.access_token is not None
        
        if not oauth_provided and not legacy_provided:
            raise ValueError("Either OAuth credentials (app_key, app_secret, refresh_token) or access_token must be provided")
        
        if oauth_provided and legacy_provided:
            # Prefer OAuth over legacy token
            self.access_token = None


@dataclass
class TranscriptionConfig:
    service: str
    api_key: str


@dataclass
class LLMConfig:
    service: str
    api_key: str
    model: str


@dataclass
class ProcessingConfig:
    compress_audio: bool
    compression_quality: str
    max_file_size_mb: int
    polling_interval: int


@dataclass
class Config:
    dropbox: DropboxConfig
    transcription: TranscriptionConfig
    llm: LLMConfig
    processing: ProcessingConfig

    @classmethod
    def load(cls) -> 'Config':
        """
        Load configuration directly from environment variables.
        """
        try:
            return cls.load_from_env()
        except ValueError as e:
            raise ValueError(
                f"Failed to load configuration from environment variables. "
                f"Please ensure all required environment variables are set. Error: {e}"
            ) from e

    @classmethod
    def load_from_env(cls) -> 'Config':
        """Load configuration directly from environment variables."""
        def get_env(var_name: str, required: bool = True, default: Optional[str] = None) -> Optional[str]:
            value = os.getenv(var_name)
            if required and value is None:
                raise ValueError(f"Required environment variable {var_name} is not set.")
            return value if value is not None else default

        dropbox_cfg = DropboxConfig(
            root_folder=get_env('DROPBOX_ROOT_FOLDER'),
            app_key=get_env('DROPBOX_APP_KEY', required=False),
            app_secret=get_env('DROPBOX_APP_SECRET', required=False),
            refresh_token=get_env('DROPBOX_REFRESH_TOKEN', required=False),
            access_token=get_env('DROPBOX_ACCESS_TOKEN', required=False)
        )

        transcription_cfg = TranscriptionConfig(
            service=get_env('TRANSCRIPTION_SERVICE'),
            api_key=get_env('TRANSCRIPTION_API_KEY')
        )

        llm_cfg = LLMConfig(
            service=get_env('LLM_SERVICE'),
            api_key=get_env('LLM_API_KEY'),
            model=get_env('LLM_MODEL')
        )

        processing_cfg = ProcessingConfig(
            compress_audio=get_env('PROCESSING_COMPRESS_AUDIO', default='true').lower() in ('true', '1', 'yes'),
            compression_quality=get_env('PROCESSING_COMPRESSION_QUALITY', default='medium'),
            max_file_size_mb=int(get_env('PROCESSING_MAX_FILE_SIZE_MB', default='100')),
            polling_interval=int(get_env('PROCESSING_POLLING_INTERVAL', default='60'))
        )

        return cls(
            dropbox=dropbox_cfg,
            transcription=transcription_cfg,
            llm=llm_cfg,
            processing=processing_cfg
        )
    
    @staticmethod
    def _resolve_env_vars(data: dict) -> dict:
        """Recursively resolve ${VAR} patterns with environment variables"""
        if isinstance(data, dict):
            return {k: Config._resolve_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [Config._resolve_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith('${') and data.endswith('}'):
            env_var = data[2:-1]
            value = os.getenv(env_var)
            if value is None:
                raise ValueError(f"Environment variable {env_var} not found")
            return value
        else:
            return data