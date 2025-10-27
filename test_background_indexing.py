#!/usr/bin/env python3
"""
Test script to verify background indexing works properly.
"""
import time
from background_indexer import BackgroundIndexer
from database import BookDatabase


def test_background_indexing():
    """Test background indexing with status updates."""
    print("=" * 70)
    print("Testing Background Indexing")
    print("=" * 70)
    print()

    bg_indexer = BackgroundIndexer()

    # Start background indexing (using test_lock.py as a dummy file)
    print("Starting background indexing...")
    success = bg_indexer.start_indexing("test_lock.py", "./chroma_db")

    if not success:
        print("Failed to start background indexing!")
        return

    print("✓ Background indexing started!")
    print()

    # Monitor status
    print("Monitoring status (for 15 seconds)...")
    for i in range(15):
        time.sleep(1)

        # Check if still running
        if bg_indexer.is_running():
            elapsed = bg_indexer.get_elapsed_time()
            print(f"[{i+1}s] Status: Running (elapsed: {elapsed})")

            # Check for updates
            updates = bg_indexer.get_all_status_updates()
            for update in updates:
                print(f"  → {update.get('status')}: {update.get('message', '')}")
        else:
            print(f"[{i+1}s] Status: Completed!")
            break

    print()

    # Get final status
    print("Final status:")
    updates = bg_indexer.get_all_status_updates()
    for update in updates:
        status = update.get('status')
        message = update.get('message', '')
        print(f"  {status}: {message}")
        if status == 'completed':
            stats = update.get('stats', {})
            print(f"    Success: {stats.get('success', 0)}, Failed: {stats.get('failed', 0)}")

    # Cleanup
    bg_indexer.cleanup()

    print()
    print("=" * 70)
    print("✓ Test completed!")
    print("=" * 70)


def test_concurrent_access():
    """Test that we can access the database while background indexing runs."""
    print()
    print("=" * 70)
    print("Testing Concurrent Database Access")
    print("=" * 70)
    print()

    bg_indexer = BackgroundIndexer()

    # Start background indexing
    print("Starting background indexing...")
    bg_indexer.start_indexing("test_lock.py", "./chroma_db")
    time.sleep(2)  # Let it start

    # Try to access database while indexing is running
    print("Attempting to open database while indexing runs...")
    try:
        db = BookDatabase("./chroma_db", verbose=True)
        print("✓ Database opened successfully!")
        print("  (Note: This might have waited for the indexing lock)")

        # Try a quick operation
        stats = db.get_stats()
        print(f"✓ Got database stats: {stats.get('total_chunks', 0)} chunks")

        db.close()
        print("✓ Database closed")
    except Exception as e:
        print(f"✗ Error accessing database: {e}")

    # Wait for background indexing to complete
    while bg_indexer.is_running():
        time.sleep(1)

    bg_indexer.cleanup()

    print()
    print("=" * 70)
    print("✓ Concurrent access test completed!")
    print("=" * 70)


if __name__ == "__main__":
    test_background_indexing()
    print()
    time.sleep(2)
    test_concurrent_access()
