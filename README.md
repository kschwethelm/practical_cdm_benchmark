# ADLM Practical WS25/26: Clinical Decision-Making LLM Benchmark


## Cluster Setup

Follow kick-off lecture slides.

### IMPORTANT

- Do NOT use home directory (`~/` or `/u/home/<in-tum-username>`)
- Use personal directory `/vol/miltank/users/<username>/`
- Fast storage for metadata `/meta/users/<username>/`

- Move all of these directories from ~/ to meta storage and symlink them:
     ```bash
     mv ~/.conda /meta/users/$USER/ && ln -s /meta/users/$USER/.conda /u/home/$USER/.conda
     mv ~/.cache /meta/users/$USER/ && ln -s /meta/users/$USER/.cache /u/home/$USER/.cache
     mv ~/.local /meta/users/$USER/ && ln -s /meta/users/$USER/.local /u/home/$USER/.local
     mv ~/.vscode-server /meta/users/$USER/ && ln -s /meta/users/$USER/.vscode-server /u/home/$USER/.vscode-server
     ```


## Installation

1. **Install [uv](https://docs.astral.sh/uv/)**

2. **Setup GitHub connection**
     - Setup username and email
          ```bash
          git config --global user.name "GITHUB-USERNAME"
          git config --global user.email "GITHUB-EMAIL"
          ```
     - Generate SSH key (see below) and add key to https://github.com/settings/keys
          ```bash
          ssh-keygen -t ed25519 -C "your_email@example.com"
          ```

3. **Setup Project Environment**
   - Clone this repository: `git clone git@github.com:kschwethelm/practical_cdm_benchmark.git`
   - Navigate to the project directory: `cd practical_cdm_benchmark`

4. **Create and Activate Virtual Environment**
     ```bash
     uv sync
     source .venv/bin/activate
     ```

5. Add a .env file following .env.template
     ```bash
      DB_NAME=...
      DB_USER=...
     ```

## Usage

1. Change download_dir var in configs/vllm_config/qwen3_4B.yaml

2. Run vLLM server on localhost

     ```bash
     uv run vllm serve --config configs/vllm_config/qwen3_4B.yaml
     ```

3. Run client test script

     ```bash
     uv run scripts/vllm_test.py
     ```