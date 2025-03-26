#!/bin/bash
cd /home/ubuntu/japanese_tutor
if [ -f tutor.pid ]; then
  pid=$(cat tutor.pid)
  echo "Stopping Japanese tutor (PID: $pid)"
  kill $pid
  rm tutor.pid
else
  echo "No running Japanese tutor found"
fi
