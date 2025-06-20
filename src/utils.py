"""
Utility functions for file processing
"""

import re
import logging
from datetime import datetime
from typing import Optional


def parse_dji_filename_date(filename: str) -> Optional[datetime]:
    """
    Parse datetime from DJI filename formats.
    
    Supports two patterns:
    - DJI_[number]_YYYYMMDD_HHMMSS[.ext] (e.g., DJI_13_20250116_110419.m4a)
    - DJI_YYYYMMDD_HHMMSS_[suffix][.ext] (e.g., DJI_20250607_110648_merged.m4a)
    
    Args:
        filename: The filename to parse
        
    Returns:
        Parsed datetime object or None if parsing fails
    """
    logger = logging.getLogger(__name__)
    
    # Remove file extension for pattern matching
    name_without_ext = filename
    if '.' in filename:
        name_without_ext = filename.rsplit('.', 1)[0]
    
    # Pattern 1: DJI_[number]_YYYYMMDD_HHMMSS
    pattern1 = r'^DJI_\d+_(\d{8})_(\d{6})$'
    match1 = re.match(pattern1, name_without_ext)
    
    if match1:
        date_str, time_str = match1.groups()
        return _parse_dji_datetime(date_str, time_str, logger)
    
    # Pattern 2: DJI_YYYYMMDD_HHMMSS_[suffix]
    pattern2 = r'^DJI_(\d{8})_(\d{6})_\w+$'
    match2 = re.match(pattern2, name_without_ext)
    
    if match2:
        date_str, time_str = match2.groups()
        return _parse_dji_datetime(date_str, time_str, logger)
    
    # No pattern matched
    logger.debug(f"DJI filename '{filename}' doesn't match expected patterns")
    return None


def _parse_dji_datetime(date_str: str, time_str: str, logger) -> Optional[datetime]:
    """
    Parse date and time strings from DJI filename into datetime object.
    
    Args:
        date_str: Date string in YYYYMMDD format
        time_str: Time string in HHMMSS format
        logger: Logger instance for error reporting
        
    Returns:
        Parsed datetime object or None if parsing fails
    """
    try:
        # Parse date components
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        
        # Parse time components
        hour = int(time_str[:2])
        minute = int(time_str[2:4])
        second = int(time_str[4:6])
        
        # Create datetime object
        parsed_dt = datetime(year, month, day, hour, minute, second)
        
        # Validate the date is reasonable (not in future, not too old)
        now = datetime.now()
        if parsed_dt > now:
            logger.warning(f"DJI date {parsed_dt} is in the future, this seems incorrect")
            return None
        
        # Reject dates older than 10 years (likely invalid)
        if (now - parsed_dt).days > 3650:
            logger.warning(f"DJI date {parsed_dt} is more than 10 years old, this seems incorrect")
            return None
        
        logger.debug(f"Successfully parsed DJI datetime: {parsed_dt}")
        return parsed_dt
        
    except (ValueError, IndexError) as e:
        logger.warning(f"Failed to parse DJI date/time components '{date_str}_{time_str}': {e}")
        return None


def is_dji_file(filename: str) -> bool:
    """
    Check if a filename appears to be from a DJI device.
    
    Args:
        filename: The filename to check
        
    Returns:
        True if filename starts with 'DJI', False otherwise
    """
    return filename.upper().startswith('DJI')