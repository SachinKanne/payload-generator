#!/usr/bin/env bash
set -euo pipefail

API_ROOT="https://performance.sfproxy.core1.perf1-useast2.aws.sfdc.cl/api/v1"
AUTH_HEADER="X-Custom-Authentication: perfS2S"
ACCEPT_HEADER="accept: application/json"

echo 'runID,payload,metrics' > runs.csv

while IFS= read -r runID || [[ -n "$runID" ]]; do
  if [[ -z "$runID" ]]; then
      continue
  fi
  echo "▶️  Processing runID: $runID"

  payload_url="$API_ROOT/perfruns/$runID"
  metrics_url="$API_ROOT/perfhub/perfrunresult_grouped/$runID"

  payload_raw=$(curl -fsSL --connect-timeout 15 -m 30 \
                 -H "$AUTH_HEADER" -H "$ACCEPT_HEADER" \
                 "$payload_url")

  payload=$(echo "$payload_raw" | jq -c '.')

  metrics_raw=$(curl -fsSL --connect-timeout 15 -m 30 \
                 -H "$AUTH_HEADER" -H "$ACCEPT_HEADER" \
                 "$metrics_url")

  metrics=$(echo "$metrics_raw" | jq -c '.')

  if [[ -n "$payload" && -n "$metrics" ]]; then
    csv_row=$(jq -cn --arg id "$runID" \
                     --arg payload "$payload" \
                     --arg metrics "$metrics" \
                     '[ $id, $payload, $metrics ] | @csv')

    if [[ -n "$csv_row" ]]; then
        echo "$csv_row" >> runs.csv
    fi
  fi

done < run_ids.txt
