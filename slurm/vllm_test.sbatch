#!/bin/bash

#SBATCH --job-name=vllm_test
#SBATCH --output=vllm_test-%A.out
#SBATCH --error=vllm_test-%A.err
#SBATCH --partition=universe,asteroids
#SBATCH --qos=phd
#SBATCH --time=0-01:00:00
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G

# Set huggingface cache
export HF_HOME=/vol/miltank/users/$USER/.cache/huggingface
export HF_HUB_CACHE=/vol/miltank/users/$USER/.cache/huggingface

# Activate uv environment
uv sync
source .venv/bin/activate

# Start vLLM server and run client
uv run vllm serve --config configs/vllm_config/qwen3_4B.yaml &
VLLM_PID=$!

# Wait until vLLM server started
SERVER_READY=false
for i in {1..200}; do
    if curl -s http://127.0.0.1:8000/health > /dev/null; then
        echo "vLLM server is up"
        SERVER_READY=true
        break
    fi
    sleep 2
done

if $SERVER_READY; then
    # RUN SCRIPT
    uv run scripts/vllm_test.py
else
    echo "vLLM server failed to start after 400 seconds. Try again or increase the wait time."
    exit 1
fi

# Kill vllm server
cleanup() {
    echo "Cleaning up..."
    kill $VLLM_PID 2>/dev/null || true
}
trap cleanup EXIT