#!/bin/bash

#SBATCH --job-name=oasst-run
#SBATCH --output=oasst-run-%A.out
#SBATCH --error=oasst-run-%A.err
#SBATCH --partition=universe,asteroids # Use  SBATCH --nodelist to specify a specific node to use in the partition
#SBATCH --time=0-06:00:00
#SBATCH --qos=master
#SBATCH --gres=gpu:2 # Make sure this number matches the tensor-parallel-size in the model's config file, also adjust max_concurrent_requests in base.yaml such that it's 4-5 * no. of GPUs  
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G

# Set huggingface cache
export HF_HOME=/vol/miltank/users/$USER/.cache/huggingface
export HF_HUB_CACHE=/vol/miltank/users/$USER/.cache/huggingface
export HF_TOKEN = $TOKEN

# Activate uv environment - if you add a new dependency, run uv sync in terminal not in here. Then run sbatch. 
source .venv/bin/activate

export RAY_RUNTIME_ENV_EXCLUDES='["llm-weights", ".venv"]'

# Start vLLM server and run client
uv run vllm serve --config configs/vllm_config/no_tool_calling/oasst_70B.yaml &
VLLM_PID=$!

# Wait until vLLM server started
# 800 * 5 sec - gives it just over an hour to start (should be enough time but increase if necessary) 
SERVER_READY=false
for i in {1..800}; do
    if curl -s http://127.0.0.1:8000/health > /dev/null; then
        echo "vLLM server is up"
        SERVER_READY=true
        break
    fi
    sleep 5
done

if $SERVER_READY; then
    # RUN SCRIPT
    uv run scripts/run_benchmark_full_info.py model_name=oasst
else
	echo "vLLM server failed to start after 4000 seconds (66 minutes). Try again or increase the wait time."
    exit 1
fi

# Kill vllm server
cleanup() {
    echo "Cleaning up..."
    kill $VLLM_PID 2>/dev/null || true
}
trap cleanup EXIT
