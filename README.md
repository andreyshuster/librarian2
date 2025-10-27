# 📚 Librarian - Semantic Book Search Agent

A powerful book search agent that lets you search through your personal library using natural language queries. It supports PDF, EPUB, and FB2 formats with semantic search powered by local AI models.

## Features

- **Natural Language Search**: Ask questions about your books in plain English
- **Semantic Understanding**: Finds books by meaning, not just keywords
- **Multiple Formats**: Supports PDF, EPUB, and FB2 files
- **Local AI**: Uses sentence-transformers for privacy (no API keys needed)
- **Background Indexing**: Index books while continuing to search
- **Pre-flight Check**: Scan directories to find new books before indexing
- **Graceful Interruption**: Ctrl-C saves progress during indexing
- **Configurable Database**: Specify custom database location
- **Fast Indexing**: Chunks books intelligently for better search results
- **Beautiful CLI**: Rich text interface with colors and formatting

## Installation

1. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Quick Start

Index a directory and start searching:
```bash
./librarian.py /path/to/your/books
```

Or start the chat interface without indexing:
```bash
./librarian.py
```

### Command-Line Options

**Check for new books before indexing:**
```bash
./librarian.py --check /path/to/your/books
```

**Use a custom database location:**
```bash
./librarian.py -d /path/to/custom/db
./librarian.py /path/to/books -d /path/to/custom/db
```

**View all options:**
```bash
./librarian.py --help
```

### Chat Commands

Once in the chat interface:

- **Search**: Just type your question naturally
  - "Show me books about artificial intelligence"
  - "Find books with romance and adventure"
  - "What books discuss machine learning?"

- **Index books**: `/index <path>`
  - `/index ~/Documents/Books` - Index a directory (foreground)
  - `/index ~/book.pdf` - Index a single file

- **Background indexing**: `/index-bg <path>`
  - `/index-bg ~/Documents/Books` - Index in background while you search
  - `/index-status` - Check background indexing progress

- **Check for new books**: `/check <path>`
  - `/check ~/Documents/Books` - Scan directory for unindexed books

- **View stats**: `/stats`
- **Help**: `/help`
- **Exit**: `/quit` or `/exit` or `Ctrl+C` (saves progress)

### Index Books Separately

You can also index books using the indexer script:
```bash
./venv/bin/python indexer.py /path/to/your/books
```

## Examples

### Example Queries

```
You: Show me books about space exploration
📖 Found 3 matching book(s)
┌─────────────────────┬──────────────┬────────┬─────────────────────┐
│ Title               │ Author       │ Format │ Match               │
├─────────────────────┼──────────────┼────────┼─────────────────────┤
│ The Martian         │ Andy Weir    │ EPUB   │ Space mission to... │
│ Cosmos              │ Carl Sagan   │ PDF    │ Exploration of...   │
└─────────────────────┴──────────────┴────────┴─────────────────────┘

You: Books written in 19th century with romance
You: Technical books about Python programming
You: Fiction with strong female protagonists
```

## How It Works

1. **Extraction**: The system extracts text from PDF, EPUB, and FB2 files
2. **Chunking**: Books are split into overlapping chunks for better context
3. **Embedding**: Each chunk is converted to a vector using sentence-transformers
4. **Storage**: Vectors are stored in ChromaDB for fast semantic search
5. **Search**: Your queries are embedded and matched against stored chunks
6. **Results**: Books are ranked by semantic similarity and deduplicated

## Architecture

```
librarian.py           - Main chat interface with command handling
indexer.py             - Book indexing pipeline with pre-flight checks
background_indexer.py  - Non-blocking background indexing
database.py            - ChromaDB manager with lock management
db_lock.py             - File-based locking for concurrent access
extractors.py          - Text extraction (PDF/EPUB/FB2)
chroma_db/             - Database storage (created automatically)
```

## Key Features Explained

### Background Indexing

Index large collections without blocking searches:
```bash
/index-bg ~/Documents/Books
# Continue searching while indexing runs in background
/index-status  # Check progress
```

### Pre-flight Check

Scan directories to see what's new before indexing:
```bash
./librarian.py --check ~/Documents/Books
```

Output shows:
- Total books found
- Already indexed count
- New books list

### Graceful Interruption

Press `Ctrl-C` during indexing to safely stop:
- Current book processing completes
- All indexed books are saved to database
- Database locks are properly released
- No data corruption

### Custom Database Location

Manage multiple book collections:
```bash
./librarian.py -d ~/scifi-db
./librarian.py -d ~/textbooks-db
```

## Supported Formats

- **PDF** (.pdf) - Using pypdf
- **EPUB** (.epub) - Using ebooklib
- **FB2** (.fb2) - FictionBook 2.0 XML format

## Database

The system uses ChromaDB to store book embeddings locally in the `chroma_db/` directory. The database persists between sessions, so you only need to index your books once.

To reset the database, simply delete the `chroma_db/` directory.

## Performance

- First run will download the embedding model (~400MB)
- Indexing speed: ~1-5 books per minute (depends on book size)
- Search speed: <1 second per query
- The more books indexed, the better the search results

## Privacy

All processing happens locally on your machine. No data is sent to external servers. The sentence-transformers model runs entirely offline.

## Troubleshooting

**Issue**: "Database is empty"
- **Solution**: Index your books using `/index <path>` command

**Issue**: Slow first search
- **Solution**: First query downloads the embedding model (~400MB), subsequent queries are fast

**Issue**: Out of memory
- **Solution**: The system processes books one at a time, but very large libraries may need more RAM

## License

GNU General Public License v3.0 - See LICENSE file for details
