#!/usr/bin/env python3
"""
Test script to verify database locking with true concurrent access.
"""
import time
import sys
import multiprocessing
from database import BookDatabase


def process_with_lock(process_id: int, hold_time: int):
    """
    Process that acquires database lock.

    Args:
        process_id: Identifier for this process
        hold_time: How long to hold the lock (seconds)
    """
    start = time.time()
    print(f"[{start:.3f}] Process {process_id}: Starting, attempting to acquire lock...")

    db = BookDatabase('./chroma_db', verbose=True)

    acquired = time.time()
    print(f"[{acquired:.3f}] Process {process_id}: Lock acquired after {acquired-start:.2f}s! Holding for {hold_time} seconds...")

    # Simulate work
    for i in range(hold_time):
        time.sleep(1)
        print(f"[{time.time():.3f}] Process {process_id}: Working... {i+1}/{hold_time}")

    print(f"[{time.time():.3f}] Process {process_id}: Releasing lock...")
    db.close()

    released = time.time()
    print(f"[{released:.3f}] Process {process_id}: Done! (total time: {released-start:.2f}s)")


def main():
    """Run two processes concurrently."""
    print("=" * 70)
    print("Testing concurrent database access with file locking")
    print("=" * 70)
    print()

    # Create two processes that will try to access the database concurrently
    p1 = multiprocessing.Process(target=process_with_lock, args=(1, 5))
    p2 = multiprocessing.Process(target=process_with_lock, args=(2, 3))

    # Start both processes at nearly the same time
    print("Starting both processes concurrently...")
    p1.start()
    time.sleep(0.1)  # Small delay to ensure p1 starts first
    p2.start()

    # Wait for both to complete
    p1.join()
    p2.join()

    print()
    print("=" * 70)
    print("✓ Test completed successfully!")
    print("If process 2 waited for process 1 to release the lock, then the")
    print("database lock is working correctly!")
    print("=" * 70)


if __name__ == "__main__":
    main()
