#!/usr/bin/env bash
set -e
export PIO_APP_NAME=`cat engine.json | grep appName | head -n 1 | sed -r 's/\s*"appName": "([^"]+)",?\s*/\1/'`
if [ -z "$PIO_APP_NAME" ]; then
  exit 1;
fi

sudo chown predictionio:root /PredictionIO-0.12.0-incubating/vendors/hbase-1.2.6/data
sudo chown predictionio:root /PredictionIO-0.12.0-incubating/vendors/elasticsearch-5.5.2/data
sudo chown predictionio:predictionio /home/predictionio/.pio_store

pio-start-all
pio status || pio status # give a second try
export PIO_APP_ID=`(pio app show "$PIO_APP_NAME" 2>/dev/null || pio app new "$PIO_APP_NAME") | grep ID | tail -n 1 | awk -F: '{ gsub(/[ ]/, "", $2); print $2}'`
