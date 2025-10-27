#!/usr/bin/env python3
"""
Simple test script to verify the system works.
"""
from database import BookDatabase
from rich.console import Console

console = Console()


def test_database():
    """Test basic database operations."""
    console.print("\n[bold cyan]Testing Database...[/bold cyan]")

    # Initialize database
    db = BookDatabase("./test_chroma_db")

    # Test adding a mock book
    mock_book = {
        'title': 'Test Book',
        'author': 'Test Author',
        'filename': 'test.pdf',
        'format': '.pdf',
        'content': 'This is a test book about artificial intelligence and machine learning. '
                   'It covers topics like neural networks, deep learning, and natural language processing. '
                   'The book also discusses computer vision and reinforcement learning algorithms.',
        'length': 200
    }

    console.print("Adding mock book to database...")
    success = db.add_book(mock_book)

    if success:
        console.print("[green]✓ Book added successfully[/green]")
    else:
        console.print("[red]✗ Failed to add book[/red]")
        return False

    # Test search
    console.print("\nTesting search...")
    results = db.search("machine learning algorithms", n_results=1)

    if results:
        console.print(f"[green]✓ Search returned {len(results)} result(s)[/green]")
        console.print(f"  Title: {results[0]['title']}")
        console.print(f"  Author: {results[0]['author']}")
        console.print(f"  Relevance: {results[0]['relevance_score']:.2%}")
    else:
        console.print("[red]✗ Search returned no results[/red]")
        return False

    # Test stats
    console.print("\nGetting database stats...")
    stats = db.get_stats()
    console.print(f"  Total chunks: {stats.get('total_chunks', 0)}")

    # Cleanup
    console.print("\nCleaning up test database...")
    import shutil
    import os
    if os.path.exists("./test_chroma_db"):
        shutil.rmtree("./test_chroma_db")
    console.print("[green]✓ Cleanup complete[/green]")

    return True


def test_imports():
    """Test that all required modules can be imported."""
    console.print("\n[bold cyan]Testing Imports...[/bold cyan]")

    modules = [
        ('chromadb', 'ChromaDB'),
        ('sentence_transformers', 'Sentence Transformers'),
        ('pypdf', 'PyPDF'),
        ('ebooklib', 'EbookLib'),
        ('bs4', 'BeautifulSoup4'),
        ('lxml', 'LXML'),
        ('rich', 'Rich')
    ]

    all_ok = True
    for module_name, display_name in modules:
        try:
            __import__(module_name)
            console.print(f"[green]✓ {display_name}[/green]")
        except ImportError as e:
            console.print(f"[red]✗ {display_name}: {e}[/red]")
            all_ok = False

    return all_ok


def main():
    """Run all tests."""
    console.print("[bold]📚 Librarian System Test[/bold]")

    # Test imports
    if not test_imports():
        console.print("\n[red]Some imports failed. Please check your installation.[/red]")
        return

    console.print()

    # Test database
    if not test_database():
        console.print("\n[red]Database tests failed.[/red]")
        return

    console.print("\n[bold green]✓ All tests passed! System is ready to use.[/bold green]")
    console.print("\n[cyan]Run './venv/bin/python librarian.py' to start the chat interface.[/cyan]\n")


if __name__ == "__main__":
    main()
