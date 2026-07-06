#!/bin/bash
# Health check simple para usar manualmente o como probe local.
# Uso: ./healthcheck.sh [host] [puerto]
HOST=${1:-localhost}
PORT=${2:-8080}

resp=$(curl -s -o /dev/null -w "%{http_code}" "http://$HOST:$PORT/health")

if [ "$resp" == "200" ]; then
  echo "OK - servicio saludable ($HOST:$PORT)"
  exit 0
else
  echo "FALLA - código HTTP $resp en $HOST:$PORT"
  exit 1
fi
