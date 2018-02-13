#!/usr/bin/env bash
set -e
source /prepare-engine.sh
# deploys app if possible (ignore otherwise)
nohup pio deploy >bootstrap-pio-deploy.log 2>&1 &
"${@}"

