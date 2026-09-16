#!/usr/bin/env bash
# Rent a GPU box on Vast.ai and start Recursa's server on it.
#   pip install vastai && vastai set api-key <YOUR_KEY>
#   RECURSA_TOKENS=<long-random> MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507-FP8 TP=4 bash vast_launch.sh
set -euo pipefail
: "${RECURSA_TOKENS:?set RECURSA_TOKENS}"
MODEL=${MODEL:-Qwen/Qwen3-235B-A22B-Instruct-2507-FP8}; TP=${TP:-4}
OFFER=$(vastai search offers "num_gpus=${TP} gpu_ram>=80 reliability>0.98 inet_down>500 direct_port_count>=2" -o 'dph' --raw \
        | python3 -c 'import json,sys; o=json.load(sys.stdin); print(o[0]["id"])')
echo "Renting offer $OFFER"
vastai create instance "$OFFER" --image vllm/vllm-openai:latest --disk 300 \
  --env "-p 8080:8080 -e RECURSA_TOKENS=${RECURSA_TOKENS} -e MODEL=${MODEL} -e TP=${TP} -e VAST_API_KEY=${VAST_API_KEY:-} -e IDLE_MINUTES=${IDLE_MINUTES:-30}" \
  --onstart vast_onstart.sh
echo "When it is running: vastai show instances  -> use http://<public_ip>:<mapped 8080>/v1 in Recursa, with your token."
echo "Put a stable HTTPS name in front (Cloudflare Tunnel or Tailscale) before sharing it with a tester."
