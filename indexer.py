"""
Book indexing pipeline to process and add books to the database.
"""
from pathlib import Path
from typing import List
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.console import Console
from database import BookDatabase
from extractors import extract_book


console = Console()


class BookIndexer:
    """Indexes books from a directory into the database."""

    SUPPORTED_FORMATS = {'.pdf', '.epub', '.fb2'}

    def __init__(self, db_path: str = "./chroma_db", db: BookDatabase = None):
        """
        Initialize the indexer.

        Args:
            db_path: Path to the database (ignored if db is provided)
            db: Optional existing BookDatabase instance to reuse
        """
        self.db = db if db is not None else BookDatabase(db_path)
        self._owns_db = db is None  # Track if we created the db

    def find_books(self, directory: Path) -> List[Path]:
        """
        Find all supported book files in a directory.

        Args:
            directory: Directory to search

        Returns:
            List of book file paths
        """
        books = []
        for ext in self.SUPPORTED_FORMATS:
            books.extend(directory.rglob(f"*{ext}"))
        return sorted(books)

    def index_directory(self, directory: str, recursive: bool = True) -> dict:
        """
        Index all books in a directory.

        Args:
            directory: Path to the directory containing books
            recursive: Whether to search subdirectories

        Returns:
            Dictionary with indexing statistics
        """
        dir_path = Path(directory)

        if not dir_path.exists():
            console.print(f"[red]Error: Directory '{directory}' does not exist[/red]")
            return {'success': 0, 'failed': 0, 'skipped': 0}

        console.print(f"\n[cyan]Scanning for books in: {directory}[/cyan]")

        # Find all books
        if recursive:
            books = self.find_books(dir_path)
        else:
            books = [f for f in dir_path.iterdir()
                     if f.is_file() and f.suffix.lower() in self.SUPPORTED_FORMATS]

        if not books:
            console.print("[yellow]No supported books found[/yellow]")
            return {'success': 0, 'failed': 0, 'skipped': 0}

        console.print(f"[green]Found {len(books)} book(s)[/green]\n")

        # Index books with progress bar
        stats = {'success': 0, 'failed': 0, 'skipped': 0}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:

            task = progress.add_task("[cyan]Indexing books...", total=len(books))

            for book_path in books:
                progress.update(task, description=f"[cyan]Processing: {book_path.name}")

                # Extract book content
                book_data = extract_book(book_path)

                if book_data is None:
                    stats['failed'] += 1
                    progress.advance(task)
                    continue

                # Add to database
                success = self.db.add_book(book_data)

                if success:
                    stats['success'] += 1
                else:
                    stats['failed'] += 1

                progress.advance(task)

        # Print summary
        console.print("\n[bold green]Indexing Complete![/bold green]")
        console.print(f"  ✓ Successfully indexed: {stats['success']}")
        if stats['failed'] > 0:
            console.print(f"  ✗ Failed: {stats['failed']}")

        return stats

    def index_file(self, file_path: str) -> bool:
        """
        Index a single book file.

        Args:
            file_path: Path to the book file

        Returns:
            True if successful, False otherwise
        """
        path = Path(file_path)

        if not path.exists():
            console.print(f"[red]Error: File '{file_path}' does not exist[/red]")
            return False

        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            console.print(f"[red]Error: Unsupported format '{path.suffix}'[/red]")
            console.print(f"[yellow]Supported formats: {', '.join(self.SUPPORTED_FORMATS)}[/yellow]")
            return False

        console.print(f"[cyan]Extracting content from: {path.name}[/cyan]")

        # Extract book content
        book_data = extract_book(path)

        if book_data is None:
            console.print("[red]Failed to extract book content[/red]")
            return False

        # Add to database
        success = self.db.add_book(book_data)

        if success:
            console.print("[green]Book indexed successfully![/green]")
        else:
            console.print("[red]Failed to index book[/red]")

        return success

    def get_stats(self):
        """Print database statistics."""
        stats = self.db.get_stats()
        console.print("\n[bold cyan]Database Statistics:[/bold cyan]")
        console.print(f"  Total indexed chunks: {stats.get('total_chunks', 0)}")
        console.print(f"  Collection: {stats.get('collection_name', 'N/A')}")

    def close(self):
        """Close the database if we own it."""
        if self._owns_db and self.db:
            self.db.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python indexer.py <directory_or_file>")
        sys.exit(1)

    path = sys.argv[1]
    indexer = BookIndexer()

    try:
        if Path(path).is_dir():
            indexer.index_directory(path)
        else:
            indexer.index_file(path)

        indexer.get_stats()
    finally:
        indexer.close()
