#!/usr/bin/env bash
# Lance jevos (port 8018) si besoin, puis le jeu (http://127.0.0.1:8080).
set -e
cd "$(dirname "$0")"
[ -x jevos/jev ] || ./setup.sh
JEVOS_PORT="${JEVOS_PORT:-8018}"
export JEVOS_URL="http://127.0.0.1:${JEVOS_PORT}"

if ! curl -sf "$JEVOS_URL/health" >/dev/null; then
  echo "Démarrage de jevos sur le port $JEVOS_PORT..."
  ./jevos/jev serve --port "$JEVOS_PORT" > jevos.log 2>&1 &
  JEVOS_PID=$!
  trap 'kill $JEVOS_PID 2>/dev/null' EXIT
  for _ in $(seq 1 30); do curl -sf "$JEVOS_URL/health" >/dev/null && break; sleep 0.5; done
fi
curl -sf "$JEVOS_URL/health" >/dev/null && echo "jevos prêt." || echo "Attention : jevos ne répond pas (voir jevos.log)."

python3 server.py
