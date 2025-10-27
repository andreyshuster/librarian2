"""
Database manager for book content using ChromaDB with semantic search.
"""
import chromadb
from chromadb.config import Settings
from pathlib import Path
from typing import List, Dict, Optional
import hashlib
from db_lock import DatabaseLock


class BookDatabase:
    """Manages book content storage and retrieval using ChromaDB."""

    def __init__(self, db_path: str = "./chroma_db", verbose: bool = True):
        """
        Initialize the database.

        Args:
            db_path: Path to store the ChromaDB database
            verbose: Whether to print status messages
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose

        # Acquire database lock to prevent concurrent access
        self.lock = DatabaseLock(db_path, timeout=None, verbose=verbose)
        if not self.lock.acquire():
            raise RuntimeError("Could not acquire database lock")

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Check if this is the first time by seeing if collection exists
        existing_collections = [col.name for col in self.client.list_collections()]
        is_first_time = "books" not in existing_collections

        if is_first_time and self.verbose:
            print("⏳ First-time setup: Downloading embedding model (this may take 30-60 seconds)...")
            print("   This is a one-time operation and will be much faster afterwards.")

        # Get or create the collection
        # Using default embedding function (sentence-transformers)
        self.collection = self.client.get_or_create_collection(
            name="books",
            metadata={"description": "Book library with full-text semantic search"}
        )

        if is_first_time and self.verbose:
            print("✓ Model ready!")

    def _generate_book_id(self, file_path: str) -> str:
        """Generate a unique ID for a book based on its path."""
        return hashlib.md5(file_path.encode()).hexdigest()

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into overlapping chunks for better search results.

        Args:
            text: The text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Number of overlapping characters between chunks

        Returns:
            List of text chunks
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundaries
            if end < len(text):
                # Look for the last period, question mark, or exclamation mark
                last_sentence = max(
                    chunk.rfind('. '),
                    chunk.rfind('? '),
                    chunk.rfind('! ')
                )
                if last_sentence > chunk_size // 2:  # Only if it's not too early
                    chunk = chunk[:last_sentence + 1]
                    end = start + last_sentence + 1

            chunks.append(chunk.strip())
            start = end - overlap

        return chunks

    def add_book(self, book_data: Dict) -> bool:
        """
        Add a book to the database.

        Args:
            book_data: Dictionary containing book metadata and content

        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate book ID
            book_id = self._generate_book_id(book_data['filename'])

            # Check if book already exists
            try:
                existing = self.collection.get(ids=[book_id])
                if existing['ids']:
                    print(f"Book already indexed: {book_data['filename']}")
                    return True
            except:
                pass

            # Chunk the content for better search results
            content = book_data.get('content', '')
            if not content:
                print(f"No content to index for {book_data['filename']}")
                return False

            chunks = self._chunk_text(content)

            # Prepare metadata (without content to save space)
            metadata = {
                'title': str(book_data.get('title', 'Unknown')),
                'author': str(book_data.get('author', 'Unknown')),
                'filename': str(book_data.get('filename', '')),
                'format': str(book_data.get('format', '')),
                'length': str(book_data.get('length', 0))
            }

            # Create IDs and metadata for each chunk
            chunk_ids = [f"{book_id}_chunk_{i}" for i in range(len(chunks))]
            chunk_metadatas = [
                {**metadata, 'chunk_id': str(i), 'total_chunks': str(len(chunks))}
                for i in range(len(chunks))
            ]

            # Add to ChromaDB
            self.collection.add(
                documents=chunks,
                ids=chunk_ids,
                metadatas=chunk_metadatas
            )

            print(f"✓ Indexed: {book_data['title']} by {book_data['author']} ({len(chunks)} chunks)")
            return True

        except Exception as e:
            print(f"Error adding book to database: {e}")
            return False

    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        Search for books using natural language query.

        Args:
            query: Natural language search query
            n_results: Maximum number of results to return

        Returns:
            List of matching books with metadata and relevance scores
        """
        try:
            # Query ChromaDB with semantic search
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results * 3  # Get more results to deduplicate books
            )

            if not results['ids'] or not results['ids'][0]:
                return []

            # Process and deduplicate results (group by book)
            books_map = {}

            for i, chunk_id in enumerate(results['ids'][0]):
                # Extract book ID from chunk ID
                book_id = '_'.join(chunk_id.split('_')[:-2])

                metadata = results['metadatas'][0][i]
                distance = results['distances'][0][i]
                document = results['documents'][0][i]

                if book_id not in books_map:
                    books_map[book_id] = {
                        'title': metadata['title'],
                        'author': metadata['author'],
                        'filename': metadata['filename'],
                        'format': metadata['format'],
                        'length': metadata['length'],
                        'relevance_score': 1 - distance,  # Convert distance to similarity
                        'matched_chunks': [],
                        'best_match': document[:300] + "..." if len(document) > 300 else document
                    }

                # Keep track of all matching chunks
                books_map[book_id]['matched_chunks'].append({
                    'text': document,
                    'score': 1 - distance
                })

                # Update best match if this chunk is more relevant
                if (1 - distance) > books_map[book_id]['relevance_score']:
                    books_map[book_id]['relevance_score'] = 1 - distance
                    books_map[book_id]['best_match'] = document[:300] + "..." if len(document) > 300 else document

            # Convert to list and sort by relevance
            books = list(books_map.values())
            books.sort(key=lambda x: x['relevance_score'], reverse=True)

            return books[:n_results]

        except Exception as e:
            print(f"Error searching database: {e}")
            return []

    def get_stats(self) -> Dict:
        """Get statistics about the database."""
        try:
            count = self.collection.count()
            return {
                'total_chunks': count,
                'collection_name': self.collection.name
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}

    def get_indexed_files(self) -> Dict[str, Dict]:
        """
        Get all indexed book files from the database.

        Returns:
            Dictionary mapping file paths to book metadata
        """
        try:
            # Get all documents from the collection
            results = self.collection.get()

            if not results or not results['metadatas']:
                return {}

            # Extract unique books (deduplicate chunks)
            books = {}
            for metadata in results['metadatas']:
                filename = metadata.get('filename', '')
                if filename and filename not in books:
                    books[filename] = {
                        'title': metadata.get('title', 'Unknown'),
                        'author': metadata.get('author', 'Unknown'),
                        'format': metadata.get('format', ''),
                        'length': metadata.get('length', 0)
                    }

            return books
        except Exception as e:
            print(f"Error getting indexed files: {e}")
            return {}

    def is_book_indexed(self, file_path: str) -> bool:
        """
        Check if a book is already indexed in the database.

        Args:
            file_path: Path to the book file

        Returns:
            True if indexed, False otherwise
        """
        try:
            book_id = self._generate_book_id(file_path)
            existing = self.collection.get(ids=[book_id])
            return bool(existing['ids'])
        except:
            return False

    def reset(self):
        """Reset the database (delete all data)."""
        try:
            self.client.delete_collection(name="books")

            if self.verbose:
                print("Recreating collection...")

            self.collection = self.client.create_collection(
                name="books",
                metadata={"description": "Book library with full-text semantic search"}
            )
            print("✓ Database reset successfully")
        except Exception as e:
            print(f"Error resetting database: {e}")

    def close(self):
        """Close the database and release the lock."""
        if hasattr(self, 'lock') and self.lock:
            self.lock.release()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False

    def __del__(self):
        """Cleanup: release the lock when the object is destroyed."""
        self.close()
