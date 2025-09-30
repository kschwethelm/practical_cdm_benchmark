# ADLM Practical WS25/26: Clinical Decision-Making LLM Benchmark

## Installation

1. **Install [UV](https://docs.astral.sh/uv/)**

2. **Setup Project Environment**
   - Clone this repository: `git clone https://github.com/kschwethelm/practical_cdm_benchmark.git`
   - Navigate to the project directory: `cd practical_cdm_benchmark`

3. **Create and Activate Virtual Environment**
     ```bash
     uv sync
     source .venv/bin/activate
     ```

4. Add a .env file following .env.template
     ```bash
      DB_NAME=...
      DB_USER=...
     ```

## Usage

1. Run vLLM server on localhost

     ```bash
     uv run vllm serve --config configs/vllm_config/qwen3_4B.yaml
     ```

2. Run client test script

     ```bash
     uv run scripts/vllm_test.py
     ```