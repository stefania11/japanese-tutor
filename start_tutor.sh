#!/bin/bash
cd /home/ubuntu/japanese_tutor
nohup python japanese_tutor.py > tutor.log 2>&1 &
echo $! > tutor.pid
echo "Japanese tutor started with PID $(cat tutor.pid)"
