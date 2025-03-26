#!/bin/bash
cd /home/ubuntu/japanese_tutor

# Kill any existing tutor processes
if [ -f tutor.pid ]; then
  pid=$(cat tutor.pid)
  echo "Stopping Japanese tutor (PID: $pid)"
  kill -9 $pid 2>/dev/null || echo "Process already stopped"
  rm tutor.pid
else
  echo "No running Japanese tutor found"
  # Kill any orphaned tutor processes
  pkill -f "python japanese_tutor.py" 2>/dev/null
fi

# Ensure clean start
sleep 3

echo "Starting Japanese tutor..."
nohup python japanese_tutor.py > tutor.log 2>&1 &
echo $! > tutor.pid
echo "Japanese tutor started with PID $(cat tutor.pid)"
echo "Check logs with: tail -f tutor.log"
