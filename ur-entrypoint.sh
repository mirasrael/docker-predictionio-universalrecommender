#!/usr/bin/env bash
set -e
pio-start-all
pio status
if [ "$PIO_APP_NAME" ]; then
  pio app show "$PIO_APP_NAME" >/dev/null || pio app new "$PIO_APP_NAME"
  ACCESS_KEY=`pio app show "$PIO_APP_NAME" | grep Key | cut -f 7 -d ' '`
  echo "============================================"
  echo "ACCESS_KEY=$ACCESS_KEY"
  echo "============================================"
fi	
"${@}"

