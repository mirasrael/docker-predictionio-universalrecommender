#!/usr/bin/env bash
set -e
PIO_APP_NAME=`cat engine.json | grep appName | head -n 1 | sed -r 's/\s*"appName": "([^"]+)",?\s*/\1/'`
if [ -z "$PIO_APP_NAME" ]; then
  exit 1;
fi

pio-start-all
pio status
pio app show "$PIO_APP_NAME" >/dev/null || pio app new "$PIO_APP_NAME"
