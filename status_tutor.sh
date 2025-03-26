#!/bin/bash
cd /home/ubuntu/japanese_tutor
if [ -f tutor.pid ]; then
  pid=$(cat tutor.pid)
  if ps -p $pid > /dev/null; then
    echo "Japanese tutor is running (PID: $pid)"
    echo "Last 10 log entries:"
    tail -10 tutor.log
  else
    echo "Japanese tutor process not found, but PID file exists. Cleaning up."
    rm tutor.pid
  fi
else
  echo "Japanese tutor is not running"
fi
