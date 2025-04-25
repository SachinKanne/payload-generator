#!/bin/bash

OUTPUT_FILE_1="first.json"
OUTPUT_FILE_2="second.json"

API_URL_1="https://performance.sfproxy.core1.perf1-useast2.aws.sfdc.cl/api/v1/perfruns/ff0df22a-ad52-47e4-8332-419fc5740310"
API_URL_2="https://performance.sfproxy.core1.perf1-useast2.aws.sfdc.cl/api/v1/perfhub/perfrunresult_grouped/ff0df22a-ad52-47e4-8332-419fc5740310"

HEADER_AUTH="X-Custom-Authentication: perfS2S"
HEADER_ACCEPT="accept: application/json"

echo "Hitting the first API: $API_URL_1"
curl -sSL -X GET "$API_URL_1" \
  -H "$HEADER_AUTH" \
  -H "$HEADER_ACCEPT" > "$OUTPUT_FILE_1"

if [ $? -eq 0 ]; then
  echo "Response successfully saved to $OUTPUT_FILE_1"
else
  echo "Error occurred while fetching from the first API. Check $OUTPUT_FILE_1."
fi

echo "----------------------------------------"

echo "Hitting the second API: $API_URL_2"
curl -sSL -X GET "$API_URL_2" \
  -H "$HEADER_AUTH" \
  -H "$HEADER_ACCEPT" > "$OUTPUT_FILE_2"

if [ $? -eq 0 ]; then
  echo "Response successfully saved to $OUTPUT_FILE_2"
else
  echo "Error occurred while fetching from the second API. Check $OUTPUT_FILE_2."
fi

echo "----------------------------------------"
echo "Script finished."
