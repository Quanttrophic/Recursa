#!/usr/bin/env bash
# Onstart script for a Vast.ai instance (vllm/vllm-openai image). Starts vLLM
# and the Recursa server, then stops the instance after IDLE_MINUTES without a
# request, so a rented GPU is not billed while nobody studies.
#   Needs: RECURSA_TOKENS, MODEL, TP, and (for self-stop) VAST_API_KEY. CONTAINER_ID is set by Vast.
set -euo pipefail
IDLE_MINUTES=${IDLE_MINUTES:-30}
pip install --quiet fastapi "uvicorn[standard]" httpx fastembed vastai
mkdir -p /srv/recursa_server && cp /workspace/recursa_server/app.py /srv/recursa_server/app.py && touch /srv/recursa_server/__init__.py
nohup python3 -m vllm.entrypoints.openai.api_server --model "${MODEL}" --tensor-parallel-size "${TP:-1}" \
  --max-model-len 32768 --enable-auto-tool-choice --tool-call-parser hermes --port 8000 > /var/log/vllm.log 2>&1 &
cd /srv && UPSTREAM_OPENAI_URL=http://127.0.0.1:8000/v1 DEFAULT_MODEL="${MODEL}" \
  nohup uvicorn recursa_server.app:app --host 0.0.0.0 --port 8080 --access-log > /var/log/recursa.log 2>&1 &
while true; do
  sleep 60
  last=$(stat -c %Y /var/log/recursa.log)
  if [ $(( $(date +%s) - last )) -gt $(( IDLE_MINUTES * 60 )) ] && [ -n "${VAST_API_KEY:-}" ] && [ -n "${CONTAINER_ID:-}" ]; then
    vastai --api-key "$VAST_API_KEY" stop instance "$CONTAINER_ID"
  fi
done
