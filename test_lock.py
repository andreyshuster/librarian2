#!/usr/bin/env python3
"""
Test script to verify database locking works.
Run this in two separate terminals to test concurrent access.
"""
import time
import sys
from database import BookDatabase

def test_lock():
    print("Attempting to acquire database lock...")

    # This will wait for the lock if another process has it
    db = BookDatabase("./chroma_db", verbose=True)

    print("✓ Database initialized successfully!")
    print("Holding lock for 10 seconds to simulate indexing...")
    print("Try running this script in another terminal now.")

    # Simulate long-running operation (like indexing)
    for i in range(10):
        time.sleep(1)
        print(f"  Working... {i+1}/10")

    print("Releasing lock and exiting...")
    db.close()
    print("✓ Done!")

if __name__ == "__main__":
    test_lock()
