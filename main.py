#!/usr/bin/env python3
"""
Ramble - Voice Memo Processing Service
Main entry point for the daemon process
"""

import time
import logging
from pathlib import Path

from src.config import Config
from src.processor import VoiceMemoProcessor


def setup_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('ramble.log'),
            logging.StreamHandler()
        ]
    )


def main():
    """Main daemon loop"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        config = Config.load()
        processor = VoiceMemoProcessor(config)
        
        logger.info("Starting Ramble voice memo processing service")
        logger.info(f"Monitoring: {config.dropbox.root_folder}/inbox/")
        
        while True:
            try:
                processor.process_inbox()
                time.sleep(config.processing.polling_interval)
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait before retrying
                
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        return 1
    
    logger.info("Ramble service stopped")
    return 0


if __name__ == "__main__":
    exit(main())