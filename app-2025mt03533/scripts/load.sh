#!/bin/bash
# usage: ./load.sh <host> [count]
HOST=$1
COUNT=${2:-30}
for i in $(seq 1 $COUNT); do
  curl -s http://$HOST:8000/get_info
  echo
  sleep 0.2
done
