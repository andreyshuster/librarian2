"""
Database locking mechanism to prevent concurrent access from multiple processes.
"""
import fcntl
import time
import sys
from pathlib import Path
from typing import Optional


class DatabaseLock:
    """File-based lock for database access."""

    def __init__(self, db_path: str, timeout: Optional[float] = None, verbose: bool = True):
        """
        Initialize the database lock.

        Args:
            db_path: Path to the database directory
            timeout: Maximum time to wait for lock in seconds (None = wait forever)
            verbose: Whether to print status messages
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.lock_file_path = self.db_path / ".db.lock"
        self.lock_file = None
        self.timeout = timeout
        self.verbose = verbose

    def acquire(self) -> bool:
        """
        Acquire the database lock.

        Returns:
            True if lock acquired, False if timeout
        """
        try:
            # Open lock file
            self.lock_file = open(self.lock_file_path, 'w')

            # Try to acquire lock
            start_time = time.time()
            shown_waiting = False

            while True:
                try:
                    # Try non-blocking lock first
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # Lock acquired
                    if shown_waiting and self.verbose:
                        print("✓ Database lock acquired")
                    return True

                except BlockingIOError:
                    # Lock is held by another process
                    if not shown_waiting and self.verbose:
                        print("⏳ Waiting for database lock (another process is using the database)...")
                        shown_waiting = True

                    # Check timeout
                    if self.timeout is not None:
                        elapsed = time.time() - start_time
                        if elapsed >= self.timeout:
                            if self.verbose:
                                print(f"✗ Timeout waiting for database lock after {elapsed:.1f} seconds")
                            self.lock_file.close()
                            self.lock_file = None
                            return False

                    # Wait a bit before retrying
                    time.sleep(0.5)

        except Exception as e:
            if self.verbose:
                print(f"Error acquiring database lock: {e}")
            if self.lock_file:
                self.lock_file.close()
                self.lock_file = None
            return False

    def release(self):
        """Release the database lock."""
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
            except Exception as e:
                if self.verbose:
                    print(f"Error releasing database lock: {e}")
            finally:
                self.lock_file = None

    def __enter__(self):
        """Context manager entry."""
        if not self.acquire():
            raise TimeoutError("Could not acquire database lock")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()
        return False
