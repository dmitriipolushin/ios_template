#!/bin/zsh
# runflows.sh <udid> <outdir> <flow.yaml>... : Maestro flows one after another on ONE simulator,
# each in <outdir>/<flow>.<attempt>/ (run.log + out/ with the takeScreenshot PNGs), one retry
# when the run died before its first step (driver start-up on a busy Mac). Prints
# "<flow> attempt N rc=X <first FAILED line>" per run and "ALLDONE" at the end.
#
# Environment:
#   APP_ID          bundle id (required)
#   MAESTRO_ENV     extra "-e KEY=VALUE" pairs for the flows, e.g. "-e PACK_URL=http://127.0.0.1:8792"
#   FLOWS_BASE      directory the flow paths are relative to (default: current directory)
#
# Run one batch per simulator, never `booted`: several simulators can be up at once.
U=$1; OUT=$2; shift 2
[ -z "$U" -o -z "$OUT" -o -z "$APP_ID" ] && { echo "usage: APP_ID=... runflows.sh <udid> <outdir> <flow.yaml>..." >&2; exit 2; }
BASE=${FLOWS_BASE:-$PWD}
export MAESTRO_DRIVER_STARTUP_TIMEOUT=${MAESTRO_DRIVER_STARTUP_TIMEOUT:-600000}
mkdir -p "$OUT"
for f in "$@"; do
  n=$(basename "$f" .yaml)
  for attempt in 1 2; do
    R="$OUT/$n.$attempt"; mkdir -p "$R"
    case "$f" in /*) FLOW="$f";; *) FLOW="$BASE/$f";; esac
    ( cd "$R" && eval maestro --udid "$U" test -e APP_ID="$APP_ID" ${MAESTRO_ENV:-} "\"$FLOW\"" --test-output-dir "\"$R/out\"" > "$R/run.log" 2>&1 )
    rc=$?
    echo "$n attempt $attempt rc=$rc $(grep -m1 FAILED "$R/run.log" | cut -c1-150)"
    [ $rc -eq 0 ] && break
    grep -q "COMPLETED" "$R/run.log" && ! grep -q "not ready in time\|SimctlError\|TimeoutException" "$R/run.log" && break
  done
done
echo ALLDONE
