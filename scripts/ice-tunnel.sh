#!/usr/bin/env bash
# Forward the ollama server on my current PACE ICE compute node to localhost:11434.
#
# Prerequisites, in this order:
#   1. GlobalProtect connected to vpn.gatech.edu
#   2. an allocation:  salloc -p ice-gpu --gres=gpu:a100:1 --cpus-per-task=8 --mem=64G --time=05:00:00
#   3. on that compute node:  module load ollama/0.12.11
#                             OLLAMA_HOST=0.0.0.0:11434 ollama serve > ~/ollama.log 2>&1 &
#
# Then run this from the Mac and leave it open. The compute node changes with every
# allocation, so the node name is read back from squeue rather than hardcoded.
set -euo pipefail

LOGIN="${ICE_LOGIN:-amohite8@login-ice.pace.gatech.edu}"
PORT="${ICE_PORT:-11434}"
# One authenticated connection, shared by the squeue lookup and the forward. Without
# this each ssh invocation re-prompts for the password (and Duo) separately.
SOCKET="${TMPDIR:-/tmp}/ice-tunnel-$PORT.sock"

cleanup() {
  ssh -S "$SOCKET" -O exit "$LOGIN" 2>/dev/null || true
  echo "tunnel closed."
}

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "port $PORT is already in use -- a local ollama or an older tunnel is holding it" >&2
  exit 1
fi

# The PACE names only resolve on the GT network, so a DNS failure here means the VPN,
# not the cluster. Checked separately because ssh reports both as one opaque error.
if ! dig +short +time=3 +tries=1 "${LOGIN#*@}" | grep -q .; then
  echo "cannot resolve ${LOGIN#*@} -- connect GlobalProtect to vpn.gatech.edu first" >&2
  exit 1
fi

# A crashed run leaves the socket file behind; ssh -M refuses to reuse the path.
if [ -e "$SOCKET" ] && ! ssh -S "$SOCKET" -O check "$LOGIN" >/dev/null 2>&1; then
  rm -f "$SOCKET"
fi

echo "authenticating to $LOGIN (once)..."
ssh -MNf -S "$SOCKET" \
    -o ServerAliveInterval=60 -o ServerAliveCountMax=3 \
    -o ExitOnForwardFailure=yes "$LOGIN"
trap cleanup EXIT INT TERM

# %N on a running single-node job is the bare node name; -h drops the header.
NODE=$(ssh -S "$SOCKET" "$LOGIN" "squeue -u \$USER -h -t RUNNING -o '%N'" | head -1 | tr -d '[:space:]')
if [ -z "$NODE" ]; then
  echo "no RUNNING job for you on ICE -- salloc first (see the header of this script)" >&2
  exit 1
fi

echo "compute node: $NODE"
ssh -S "$SOCKET" -O forward -L "$PORT:$NODE:$PORT" "$LOGIN"

# Prove the forward actually reaches ollama, rather than leaving a silent terminal that
# looks identical whether it worked or the server on the node is down.
if curl -fsS --max-time 10 "http://localhost:$PORT/api/tags" >/dev/null 2>&1; then
  echo "tunnel up: localhost:$PORT -> $NODE:$PORT, ollama answering."
else
  echo "tunnel up, but ollama on $NODE is not answering -- is 'ollama serve' running" >&2
  echo "there, bound to 0.0.0.0:$PORT? (check ~/ollama.log on the node)" >&2
fi
echo "leave this window open; Ctrl-C to close."

# Hold the master open. It dies with this script, which is what keeps Ctrl-C meaningful.
while ssh -S "$SOCKET" -O check "$LOGIN" >/dev/null 2>&1; do sleep 5; done
echo "ssh master connection dropped (VPN drop, or the login node closed it)." >&2
