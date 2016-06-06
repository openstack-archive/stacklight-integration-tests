#!/bin/bash
set -e

# Hacky way to find out which release should be updated
RELEASE_ID=$(fuel rel | grep Ubuntu | grep -v UCA | awk '{print $1}')
TMP_FILE="$(mktemp).yaml"
fuel role --rel "$RELEASE_ID" --role controller --file "$TMP_FILE"
sed -i 's/    min: ./    min: 0/' "$TMP_FILE"
fuel role --rel 2 --update --file "$TMP_FILE"
rm -f "$TMP_FILE"
