"""
Background indexing module for non-blocking book indexing.
"""
import multiprocessing
import time
from pathlib import Path
from typing import Optional
from datetime import datetime


class BackgroundIndexer:
    """Manages background indexing operations."""

    def __init__(self):
        """Initialize the background indexer."""
        self.process: Optional[multiprocessing.Process] = None
        self.status_queue = multiprocessing.Queue()
        self.start_time: Optional[datetime] = None

    @staticmethod
    def _index_worker(path: str, db_path: str, status_queue: multiprocessing.Queue):
        """
        Worker function that runs in a separate process to index books.

        Args:
            path: Path to the file or directory to index
            db_path: Path to the database
            status_queue: Queue for sending status updates
        """
        try:
            # Import here to avoid issues with multiprocessing
            from indexer import BookIndexer
            from pathlib import Path

            status_queue.put({"status": "starting", "message": "Initializing indexer..."})

            indexer = BookIndexer(db_path)

            try:
                path_obj = Path(path)
                if path_obj.is_dir():
                    status_queue.put({"status": "running", "message": f"Indexing directory: {path}"})
                    stats = indexer.index_directory(path)
                else:
                    status_queue.put({"status": "running", "message": f"Indexing file: {path}"})
                    success = indexer.index_file(path)
                    stats = {'success': 1 if success else 0, 'failed': 0 if success else 1}

                status_queue.put({
                    "status": "completed",
                    "message": "Indexing completed successfully!",
                    "stats": stats
                })
            finally:
                indexer.close()

        except Exception as e:
            status_queue.put({
                "status": "error",
                "message": f"Indexing failed: {str(e)}",
                "error": str(e)
            })

    def start_indexing(self, path: str, db_path: str = "./chroma_db") -> bool:
        """
        Start background indexing of a file or directory.

        Args:
            path: Path to the file or directory to index
            db_path: Path to the database

        Returns:
            True if indexing started successfully, False otherwise
        """
        if self.is_running():
            return False

        # Clear old status messages
        while not self.status_queue.empty():
            try:
                self.status_queue.get_nowait()
            except:
                break

        # Start the indexing process
        self.process = multiprocessing.Process(
            target=self._index_worker,
            args=(path, db_path, self.status_queue)
        )
        self.process.start()
        self.start_time = datetime.now()
        return True

    def is_running(self) -> bool:
        """
        Check if indexing is currently running.

        Returns:
            True if indexing is in progress, False otherwise
        """
        if self.process is None:
            return False
        return self.process.is_alive()

    def get_status(self) -> Optional[dict]:
        """
        Get the latest status update from the indexing process.

        Returns:
            Status dictionary or None if no updates available
        """
        try:
            if not self.status_queue.empty():
                return self.status_queue.get_nowait()
        except:
            pass
        return None

    def get_all_status_updates(self) -> list:
        """
        Get all pending status updates.

        Returns:
            List of status dictionaries
        """
        updates = []
        while True:
            update = self.get_status()
            if update is None:
                break
            updates.append(update)
        return updates

    def get_elapsed_time(self) -> Optional[str]:
        """
        Get elapsed time since indexing started.

        Returns:
            Formatted elapsed time string or None
        """
        if self.start_time is None:
            return None

        elapsed = datetime.now() - self.start_time
        seconds = int(elapsed.total_seconds())
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}m {seconds}s"

    def stop(self):
        """Stop the background indexing process."""
        if self.process and self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=2)
            if self.process.is_alive():
                self.process.kill()
        self.process = None
        self.start_time = None

    def cleanup(self):
        """Clean up resources."""
        self.stop()
