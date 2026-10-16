#!/usr/bin/env bash
# Build the self-hosted India basemap (spec 10.2). NOT run in CI. Needs the `pmtiles` CLI
# (https://github.com/protomaps/go-pmtiles) and network access to a Protomaps planet build.
#
#   bash scripts/build-basemap.sh [MAXZOOM] [SOURCE_URL]
#
# Records the resulting size in public/tiles/india.size.txt so the number is measured, not guessed.
set -euo pipefail
MAXZOOM="${1:-11}"
# Find the current daily build at https://maps.protomaps.com/builds/ and pass its URL as $2.
SOURCE="${2:?pass a Protomaps planet .pmtiles URL as the second argument}"
OUT="$(dirname "$0")/../public/tiles/india.pmtiles"
mkdir -p "$(dirname "$OUT")"
pmtiles extract "$SOURCE" "$OUT" --bbox="68.1,6.7,97.4,35.7" --maxzoom="$MAXZOOM"
BYTES=$(wc -c < "$OUT")
echo "{\"available\": true, \"bytes\": $BYTES, \"maxzoom\": $MAXZOOM}" > "$(dirname "$OUT")/basemap.json"
echo "maxzoom=$MAXZOOM bytes=$BYTES built=$(date -u +%FT%TZ)" | tee "$(dirname "$OUT")/india.size.txt"
