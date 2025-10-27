"""
Book content extractors for PDF, EPUB, and FB2 formats.
"""
import re
from pathlib import Path
from typing import Optional
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
import pypdf


class BookExtractor:
    """Base class for book content extraction."""

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize extracted text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove page numbers and headers/footers patterns
        text = re.sub(r'\n\d+\n', '\n', text)
        return text.strip()

    @staticmethod
    def extract_metadata(file_path: Path) -> dict:
        """Extract basic metadata from filename."""
        return {
            'filename': file_path.name,
            'format': file_path.suffix.lower(),
            'size': file_path.stat().st_size
        }


class PDFExtractor(BookExtractor):
    """Extract text content from PDF files."""

    @staticmethod
    def extract(file_path: Path) -> Optional[dict]:
        """Extract text and metadata from PDF."""
        try:
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)

                # Extract metadata
                metadata = BookExtractor.extract_metadata(file_path)
                metadata['pages'] = len(reader.pages)

                # Try to get PDF metadata
                if reader.metadata:
                    metadata['title'] = reader.metadata.get('/Title', file_path.stem)
                    metadata['author'] = reader.metadata.get('/Author', 'Unknown')
                else:
                    metadata['title'] = file_path.stem
                    metadata['author'] = 'Unknown'

                # Extract text from all pages
                text_parts = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)

                full_text = '\n'.join(text_parts)
                metadata['content'] = BookExtractor.clean_text(full_text)
                metadata['length'] = len(metadata['content'])

                return metadata

        except Exception as e:
            print(f"Error extracting PDF {file_path}: {e}")
            return None


class EPUBExtractor(BookExtractor):
    """Extract text content from EPUB files."""

    @staticmethod
    def extract(file_path: Path) -> Optional[dict]:
        """Extract text and metadata from EPUB."""
        try:
            book = epub.read_epub(str(file_path))

            # Extract metadata
            metadata = BookExtractor.extract_metadata(file_path)
            metadata['title'] = book.get_metadata('DC', 'title')
            metadata['title'] = metadata['title'][0][0] if metadata['title'] else file_path.stem

            metadata['author'] = book.get_metadata('DC', 'creator')
            metadata['author'] = metadata['author'][0][0] if metadata['author'] else 'Unknown'

            # Extract text from all items
            text_parts = []
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    content = item.get_content()
                    soup = BeautifulSoup(content, 'lxml')
                    text = soup.get_text()
                    if text:
                        text_parts.append(text)

            full_text = '\n'.join(text_parts)
            metadata['content'] = BookExtractor.clean_text(full_text)
            metadata['length'] = len(metadata['content'])

            return metadata

        except Exception as e:
            print(f"Error extracting EPUB {file_path}: {e}")
            return None


class FB2Extractor(BookExtractor):
    """Extract text content from FB2 (FictionBook 2.0) files."""

    @staticmethod
    def extract(file_path: Path) -> Optional[dict]:
        """Extract text and metadata from FB2."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            soup = BeautifulSoup(content, 'lxml-xml')

            # Extract metadata
            metadata = BookExtractor.extract_metadata(file_path)

            # FB2 metadata is in the description section
            title_info = soup.find('title-info')
            if title_info:
                book_title = title_info.find('book-title')
                metadata['title'] = book_title.text.strip() if book_title else file_path.stem

                author = title_info.find('author')
                if author:
                    first_name = author.find('first-name')
                    last_name = author.find('last-name')
                    author_name = ' '.join(filter(None, [
                        first_name.text.strip() if first_name else '',
                        last_name.text.strip() if last_name else ''
                    ]))
                    metadata['author'] = author_name or 'Unknown'
                else:
                    metadata['author'] = 'Unknown'
            else:
                metadata['title'] = file_path.stem
                metadata['author'] = 'Unknown'

            # Extract text from body
            body = soup.find('body')
            if body:
                # Remove style and script tags
                for tag in body(['style', 'script']):
                    tag.decompose()
                text = body.get_text()
            else:
                text = soup.get_text()

            metadata['content'] = BookExtractor.clean_text(text)
            metadata['length'] = len(metadata['content'])

            return metadata

        except Exception as e:
            print(f"Error extracting FB2 {file_path}: {e}")
            return None


def extract_book(file_path: Path) -> Optional[dict]:
    """
    Extract content from a book file based on its format.

    Args:
        file_path: Path to the book file

    Returns:
        Dictionary with book metadata and content, or None if extraction failed
    """
    suffix = file_path.suffix.lower()

    if suffix == '.pdf':
        return PDFExtractor.extract(file_path)
    elif suffix == '.epub':
        return EPUBExtractor.extract(file_path)
    elif suffix == '.fb2':
        return FB2Extractor.extract(file_path)
    else:
        print(f"Unsupported format: {suffix}")
        return None
