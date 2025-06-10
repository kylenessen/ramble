#!/usr/bin/env python3
"""
Setup script for Ramble - Voice Memo Processing Service
"""

import os
import subprocess
import sys
from pathlib import Path


def install_requirements():
    """Install Python requirements"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Python requirements installed")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install requirements: {e}")
        return False
    return True


def check_ffmpeg():
    """Check if FFmpeg is available"""
    try:
        subprocess.check_output(["ffmpeg", "-version"], stderr=subprocess.DEVNULL)
        print("✓ FFmpeg is available")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ FFmpeg not found. Please install FFmpeg for audio compression.")
        print("  macOS: brew install ffmpeg")
        print("  Ubuntu: sudo apt install ffmpeg")
        return False


def create_config():
    """Create config.yaml from example if it doesn't exist"""
    config_path = Path("config.yaml")
    example_path = Path("config.yaml.example")
    
    if not config_path.exists() and example_path.exists():
        config_path.write_text(example_path.read_text())
        print("✓ Created config.yaml from example")
        print("⚠ Please edit config.yaml with your API keys and settings")
        return True
    elif config_path.exists():
        print("✓ config.yaml already exists")
        return True
    else:
        print("✗ config.yaml.example not found")
        return False


def create_directories():
    """Create necessary directories"""
    directories = ["processed", "logs"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ Created directory: {directory}")


def main():
    """Main setup function"""
    print("Setting up Ramble Voice Memo Processing Service...")
    print("=" * 50)
    
    success = True
    
    # Install requirements
    if not install_requirements():
        success = False
    
    # Check FFmpeg
    if not check_ffmpeg():
        success = False
    
    # Create config
    if not create_config():
        success = False
    
    # Create directories
    create_directories()
    
    print("=" * 50)
    if success:
        print("✓ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Edit config.yaml with your API keys")
        print("2. Run: python main.py")
    else:
        print("✗ Setup completed with errors")
        print("Please resolve the errors above before running the service")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())