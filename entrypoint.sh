#!/usr/bin/env bashio

set -o allexport
  ZB_ESP_DEVICE_PORT="$(bashio::config 'ZB_ESP_DEVICE_PORT')"
set +o allexport

exec nginx & python3 web.py $ZB_ESP_DEVICE_PORT
