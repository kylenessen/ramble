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
    access_token: str
    root_folder: str


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
    def load(cls, config_path: Optional[str] = None) -> 'Config':
        """Load configuration from YAML file"""
        if config_path is None:
            config_path = os.getenv('RAMBLE_CONFIG', 'config.yaml')
        
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)
        
        # Resolve environment variables
        data = cls._resolve_env_vars(data)
        
        return cls(
            dropbox=DropboxConfig(**data['dropbox']),
            transcription=TranscriptionConfig(**data['transcription']),
            llm=LLMConfig(**data['llm']),
            processing=ProcessingConfig(**data['processing'])
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