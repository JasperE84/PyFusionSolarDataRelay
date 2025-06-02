import logging
import threading
import time
from functools import wraps
from typing import Callable, Any, Optional

def rate_limit(max_calls, period):
    def decorator(func):
        last_reset = [time.time()]  # Using a list to allow access to the nonlocal variable in closures
        call_count = [0]
        lock = threading.Lock()

        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                current_time = time.time()

                # Calculate the time since the last reset
                time_since_reset = current_time - last_reset[0]

                # If the period has elapsed, reset the rate limit counter
                if time_since_reset >= period:
                    last_reset[0] = current_time
                    call_count[0] = 0

                # If the call count is within the limit, proceed
                if call_count[0] < max_calls:
                    call_count[0] += 1
                    return func(*args, **kwargs)
                else:
                    # Calculate how long to wait before retrying
                    time_to_wait = period - time_since_reset
                    time.sleep(time_to_wait)
                    # After sleeping, reset the counter and timestamp
                    last_reset[0] = time.time()
                    call_count[0] = 1  # Set to 1 because it's about to make a call
                    return func(*args, **kwargs)

        return wrapper

    return decorator


class JobTimeoutError(Exception):
    """Exception raised when a job exceeds its timeout duration."""
    pass


def job_timeout(timeout_seconds: int, logger: Optional[logging.Logger] = None):
    """
    Decorator that enforces a timeout on job execution.
    
    Args:
        timeout_seconds: Maximum time in seconds before cancelling the job
        logger: Optional logger for timeout events
    
    Raises:
        JobTimeoutError: If the job exceeds the timeout duration
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = [None]
            exception = [None]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e
            
            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            thread.join(timeout=timeout_seconds)
            
            if thread.is_alive():
                # Job is still running after timeout
                if logger:
                    logger.error(f"Job {func.__name__} exceeded timeout of {timeout_seconds} seconds and will be cancelled")
                
                # Note: We cannot forcefully kill the thread, but we can abandon it
                # The thread will continue running in the background until it completes
                # This is a limitation of Python threading, but the scheduler will be able to start new jobs
                raise JobTimeoutError(f"Job {func.__name__} exceeded timeout of {timeout_seconds} seconds")
            
            if exception[0]:
                raise exception[0]
            
            return result[0]
        
        return wrapper
    return decorator


class JobExecutionTracker:
    """
    Tracks the execution state of scheduled jobs to prevent overlapping executions
    and manage timeouts.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._running_jobs = {}
        self._lock = threading.Lock()
    
    def is_job_running(self, job_id: str) -> bool:
        """Check if a job is currently running."""
        with self._lock:
            return job_id in self._running_jobs
    
    def start_job(self, job_id: str) -> bool:
        """
        Mark a job as started.
        
        Returns:
            True if job was started successfully, False if already running
        """
        with self._lock:
            if job_id in self._running_jobs:
                return False
            
            self._running_jobs[job_id] = {
                'start_time': time.time(),
                'thread_id': threading.get_ident()
            }
            return True
    
    def finish_job(self, job_id: str):
        """Mark a job as finished."""
        with self._lock:
            if job_id in self._running_jobs:
                duration = time.time() - self._running_jobs[job_id]['start_time']
                self.logger.info(f"Job {job_id} completed in {duration:.2f} seconds")
                del self._running_jobs[job_id]
    
    def get_job_duration(self, job_id: str) -> Optional[float]:
        """Get the current duration of a running job in seconds."""
        with self._lock:
            if job_id in self._running_jobs:
                return time.time() - self._running_jobs[job_id]['start_time']
            return None
    
    def cleanup_stale_jobs(self, max_duration: float):
        """Remove jobs that have been running longer than max_duration."""
        with self._lock:
            current_time = time.time()
            stale_jobs = []
            
            for job_id, job_info in self._running_jobs.items():
                if current_time - job_info['start_time'] > max_duration:
                    stale_jobs.append(job_id)
            
            for job_id in stale_jobs:
                self.logger.warning(f"Cleaning up stale job {job_id} that exceeded {max_duration} seconds")
                del self._running_jobs[job_id]
