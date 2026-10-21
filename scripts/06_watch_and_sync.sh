#!/bin/bash
# Re-sync Supabase every 10 min while the IAPD brochure fetch is running,
# then do a final sync and build the Excel workbook.
cd "$(dirname "$0")/.."
INTERVAL=${INTERVAL:-600}
while pgrep -f 02_fetch_brochures.py >/dev/null; do
  echo "$(date '+%F %T') sync"
  python3 -I scripts/05_sync_supabase.py 2>&1 | tail -1
  sleep "$INTERVAL"
done
echo "$(date '+%F %T') fetch finished; final sync"
python3 -I scripts/05_sync_supabase.py 2>&1 | tail -1
python3 -I scripts/04_build_workbook.py 2>&1 | tail -1
