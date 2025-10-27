#!/usr/bin/env python3
"""
Librarian - A natural language book search agent.
Search your book library using semantic queries.
"""
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from database import BookDatabase
from indexer import BookIndexer


console = Console()


class Librarian:
    """Interactive chat interface for book search."""

    def __init__(self, db_path: str = "./chroma_db"):
        """Initialize the librarian."""
        self.db_path = db_path
        self.db = None  # Lazy load database
        self._indexer = None  # Lazy load indexer
        # Create prompt session with history and auto-suggestions
        self.session = PromptSession(
            history=InMemoryHistory(),
            auto_suggest=AutoSuggestFromHistory(),
            enable_history_search=True
        )

    @property
    def indexer(self):
        """Lazy load the indexer when needed."""
        if self._indexer is None:
            console.print("[dim]Initializing indexer...[/dim]")
            # Reuse the existing database instance to avoid lock conflicts
            db = self._get_database()
            self._indexer = BookIndexer(self.db_path, db=db)
        return self._indexer

    def _get_database(self):
        """Lazy load the database when needed."""
        if self.db is None:
            console.print("\n[dim]Loading database...[/dim]")
            self.db = BookDatabase(self.db_path, verbose=True)
            console.print("[dim]Database ready.[/dim]\n")
        return self.db

    def display_welcome(self):
        """Display welcome message."""
        welcome_text = """
# 📚 Librarian - Your Book Search Agent

Ask me questions about your books in natural language!

**Examples:**
- "Show me books about artificial intelligence"
- "Find books with romance and adventure"
- "What books discuss machine learning algorithms?"
- "Books about history of Rome"

**Commands:**
- `/index <path>` - Index a book file or directory
- `/stats` - Show database statistics
- `/help` - Show this help message
- `/quit` or `/exit` - Exit the program

**Editing:**
- Arrow keys ← → to move cursor and edit your message
- ↑ ↓ to browse command history
- Ctrl+R for reverse history search
- Full line editing with backspace, delete, etc.
"""
        console.print(Panel(Markdown(welcome_text), border_style="cyan", padding=(1, 2)))

    def display_results(self, results: list):
        """Display search results in a formatted table."""
        if not results:
            console.print("\n[yellow]No matching books found.[/yellow]\n")
            return

        # Create a table
        table = Table(
            title=f"\n📖 Found {len(results)} matching book(s)",
            title_style="bold green",
            show_header=True,
            header_style="bold cyan",
            border_style="blue"
        )

        table.add_column("Title", style="cyan", no_wrap=False, width=25)
        table.add_column("Author", style="magenta", width=18)
        table.add_column("Format", style="green", width=8)
        table.add_column("File", style="blue", no_wrap=False, width=30)
        table.add_column("Match", style="yellow", width=40)

        for book in results:
            # Format relevance score as percentage
            score = f"{book['relevance_score'] * 100:.1f}%"

            # Truncate best match for display
            match_text = book.get('best_match', '')
            if len(match_text) > 120:
                match_text = match_text[:117] + "..."

            # Get filename and create a clickable link using OSC 8
            filename = book.get('filename', 'Unknown')
            # Create hyperlink that opens the file when clicked (if terminal supports it)
            file_link = f"[link=file://{filename}]{filename}[/link]"

            table.add_row(
                book['title'],
                book['author'],
                book['format'].replace('.', '').upper(),
                file_link,
                match_text
            )

        console.print(table)
        console.print()

    def handle_command(self, user_input: str) -> bool:
        """
        Handle special commands.

        Returns:
            True to continue, False to quit
        """
        parts = user_input.strip().split(maxsplit=1)
        command = parts[0].lower()

        if command in ['/quit', '/exit']:
            console.print("\n[cyan]Goodbye! 👋[/cyan]\n")
            return False

        elif command == '/help':
            self.display_welcome()

        elif command == '/stats':
            db = self._get_database()
            stats = db.get_stats()
            console.print("[bold cyan]📊 Database Statistics:[/bold cyan]")
            console.print(f"  Total indexed chunks: {stats.get('total_chunks', 0)}")
            console.print(f"  Collection: {stats.get('collection_name', 'N/A')}\n")

        elif command == '/index':
            if len(parts) < 2:
                console.print("[red]Usage: /index <file_or_directory>[/red]")
            else:
                path = parts[1].strip()
                console.print()
                if Path(path).is_dir():
                    self.indexer.index_directory(path)
                else:
                    self.indexer.index_file(path)

        else:
            console.print(f"[red]Unknown command: {command}[/red]")
            console.print("[yellow]Type /help for available commands[/yellow]")

        return True

    def search(self, query: str, n_results: int = 5):
        """Search for books and display results."""
        console.print(f"\n[dim]Searching for: {query}[/dim]")

        db = self._get_database()

        # Check if database is empty (only on first search)
        if self.db is not None:  # Only check after db is loaded
            stats = db.get_stats()
            if stats.get('total_chunks', 0) == 0:
                console.print("\n[yellow]⚠️  Database is empty. Use /index <path> to add books.[/yellow]\n")
                return

        with console.status("[bold cyan]Searching...", spinner="dots"):
            results = db.search(query, n_results)

        self.display_results(results)

    def cleanup(self):
        """Clean up resources before exit."""
        # Close indexer first (won't close db if it doesn't own it)
        if self._indexer is not None:
            self._indexer.close()
        # Then close the main database
        if self.db is not None:
            self.db.close()

    def run(self):
        """Run the interactive chat interface."""
        self.display_welcome()

        # Note: We skip checking if database is empty on startup to avoid loading
        # the model immediately. The user will get feedback when they try to search.

        try:
            while True:
                try:
                    # Get user input with editing capabilities
                    console.print()  # Add newline before prompt
                    user_input = self.session.prompt("You: ", default="")

                    if not user_input.strip():
                        continue

                    # Handle commands
                    if user_input.startswith('/'):
                        should_continue = self.handle_command(user_input)
                        if not should_continue:
                            break
                    else:
                        # Perform search
                        self.search(user_input)

                except KeyboardInterrupt:
                    console.print("\n\n[cyan]Goodbye! 👋[/cyan]\n")
                    break
                except EOFError:
                    console.print("\n\n[cyan]Goodbye! 👋[/cyan]\n")
                    break
                except Exception as e:
                    console.print(f"\n[red]Error: {e}[/red]\n")
        finally:
            # Always cleanup resources
            self.cleanup()


def main():
    """Main entry point."""
    # Check if a directory was provided as argument
    if len(sys.argv) > 1:
        # If argument provided, index it first then start chat
        path = sys.argv[1]
        console.print(f"[cyan]Indexing books from: {path}[/cyan]\n")

        indexer = BookIndexer()
        try:
            if Path(path).is_dir():
                indexer.index_directory(path)
            else:
                indexer.index_file(path)
        finally:
            # Clean up indexer
            indexer.close()

        console.print()

    # Start the interactive chat
    librarian = Librarian()
    librarian.run()


if __name__ == "__main__":
    main()
