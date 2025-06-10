"""
Error handling and retry logic for the Ramble service
"""

import logging
import time
from functools import wraps
from typing import Callable, Any, Optional, Tuple, Type


class RetryError(Exception):
    """Exception raised when maximum retries are exceeded"""
    pass


class ErrorHandler:
    """Handles error recovery and retry logic"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.logger = logging.getLogger(__name__)
    
    def retry_with_backoff(
        self,
        func: Callable,
        *args,
        max_retries: Optional[int] = None,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
        backoff_factor: float = 2.0,
        **kwargs
    ) -> Any:
        """
        Retry a function with exponential backoff
        
        Args:
            func: Function to retry
            *args: Arguments to pass to func
            max_retries: Maximum number of retries (None uses default)
            exceptions: Tuple of exceptions to catch and retry on
            backoff_factor: Factor to multiply delay by on each retry
            **kwargs: Keyword arguments to pass to func
        
        Returns:
            Result of successful function call
            
        Raises:
            RetryError: If maximum retries exceeded
        """
        retries = max_retries or self.max_retries
        delay = self.base_delay
        
        for attempt in range(retries + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                if attempt == retries:
                    self.logger.error(f"Function {func.__name__} failed after {retries} retries: {e}")
                    raise RetryError(f"Maximum retries ({retries}) exceeded for {func.__name__}: {e}")
                
                self.logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                self.logger.info(f"Waiting {delay:.1f}s before retry...")
                time.sleep(delay)
                delay *= backoff_factor
    
    def safe_operation(
        self,
        func: Callable,
        *args,
        operation_name: str = "operation",
        **kwargs
    ) -> Tuple[bool, Any]:
        """
        Safely execute an operation with error handling
        
        Args:
            func: Function to execute
            *args: Arguments to pass to func
            operation_name: Name of operation for logging
            **kwargs: Keyword arguments to pass to func
            
        Returns:
            Tuple of (success: bool, result: Any)
        """
        try:
            result = func(*args, **kwargs)
            self.logger.info(f"{operation_name} completed successfully")
            return True, result
        except Exception as e:
            self.logger.error(f"{operation_name} failed: {e}")
            return False, None


def retry_on_failure(
    max_retries: int = 3,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    backoff_factor: float = 2.0,
    base_delay: float = 1.0
):
    """
    Decorator for automatic retry with exponential backoff
    
    Args:
        max_retries: Maximum number of retries
        exceptions: Tuple of exceptions to catch and retry on
        backoff_factor: Factor to multiply delay by on each retry
        base_delay: Initial delay between retries
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = ErrorHandler(max_retries, base_delay)
            return handler.retry_with_backoff(
                func,
                *args,
                max_retries=max_retries,
                exceptions=exceptions,
                backoff_factor=backoff_factor,
                **kwargs
            )
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern for handling repeated failures
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.logger = logging.getLogger(__name__)
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker
        
        Args:
            func: Function to execute
            *args: Arguments to pass to func
            **kwargs: Keyword arguments to pass to func
            
        Returns:
            Result of function call
            
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                self.logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN - operation blocked")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful operation"""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.logger.info("Circuit breaker reset to CLOSED state")
        self.failure_count = 0
        self.last_failure_time = None
    
    def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


# Common error types for the Ramble service
class RambleError(Exception):
    """Base exception for Ramble service errors"""
    pass


class TranscriptionError(RambleError):
    """Exception for transcription service errors"""
    pass


class LLMProcessingError(RambleError):
    """Exception for LLM processing errors"""
    pass


class DropboxError(RambleError):
    """Exception for Dropbox API errors"""
    pass


class FileProcessingError(RambleError):
    """Exception for file processing errors"""
    pass