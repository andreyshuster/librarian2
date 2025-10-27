#!/bin/bash
# Test concurrent database access

echo "Starting first process (will hold lock for 10 seconds)..."
python test_lock.py &
PID1=$!

# Wait a bit to ensure first process has the lock
sleep 2

echo ""
echo "Starting second process (should wait for lock)..."
python test_lock.py &
PID2=$!

# Wait for both to complete
wait $PID1
wait $PID2

echo ""
echo "Both processes completed successfully!"
