# ADLM Practical WS25/26: Clinical Decision-Making LLM Benchmark

> :warning: Complete MIMIC training BEFORE using any MIMIC data: https://physionet.org/content/mimiciv/view-required-training/3.1/#1

## Cluster Setup

Follow kick-off lecture slides.

### Storage Configuration

**Important:** Do NOT use home directory (`~/` or `/u/home/<in-tum-username>`)

- Personal directory: `/vol/miltank/users/<username>/`
- Fast metadata storage: `/meta/users/<username>/`

Move these directories from `~/` to meta storage and create symlinks:

```bash
mv ~/.conda /meta/users/$USER/ && ln -s /meta/users/$USER/.conda /u/home/$USER/.conda
mv ~/.cache /meta/users/$USER/ && ln -s /meta/users/$USER/.cache /u/home/$USER/.cache
mv ~/.local /meta/users/$USER/ && ln -s /meta/users/$USER/.local /u/home/$USER/.local
mv ~/.vscode-server /meta/users/$USER/ && ln -s /meta/users/$USER/.vscode-server /u/home/$USER/.vscode-server
```


## Installation

1. **Install [uv](https://docs.astral.sh/uv/)**
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```

2. **Setup GitHub Connection**
   - Set username and email:
     ```bash
     git config --global user.name "GITHUB-USERNAME"
     git config --global user.email "GITHUB-EMAIL"
     ```
   - Generate SSH key and add to [GitHub SSH keys](https://github.com/settings/keys):
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

5. **Create Environment File**

   Create a `.env` file following `.env.template`:
   ```bash
   DB_NAME=...
   DB_USER=...
   ```

## Usage

1. Update `download_dir` variable in [configs/vllm_config/qwen3_4B.yaml](configs/vllm_config/qwen3_4B.yaml)

### On Cluster (Slurm)

2. Run slurm script:
   ```bash
   sbatch slurm/vllm_test.sbatch
   ```

### On Local PC/Workstation

2. Run vLLM server on localhost:
   ```bash
   uv run vllm serve --config configs/vllm_config/qwen3_4B.yaml
   ```

3. Open another terminal and run client script:
   ```bash
   uv run scripts/vllm_test.py
   ```

## Create Database from Scratch

Follow these steps to set up the database on a local machine/workstation.

### Install PostgreSQL

Steps for Ubuntu:

1. Install PostgreSQL:
   ```bash
   sudo apt install postgresql
   ```

2. Create database (trust localhost connections = no password):
   ```bash
   initdb -D "$DB_DIR" -U "$DB_USER" -A trust
   createdb -h 127.0.0.1 -U "$DB_USER" "mimiciv_pract"
   ```

### Create MIMIC Database

1. Download MIMIC-IV hosp `*.csv.gz` files from https://physionet.org/content/mimiciv/3.1/

2. Run the following commands:

   ```bash
   MIMIC_DIR=/opt/mimic/mimiciv/3.1/

   # Create (empty) tables
   psql -d mimiciv_pract -f database/sql/create.sql

   # Load data into tables
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -v mimic_data_dir=$MIMIC_DIR -f database/sql/load_gz.sql

   # Set primary keys, indexes, etc.
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -f database/sql/constraint.sql
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -f database/sql/index.sql

   # Assign lab and microbiology events to hadm_id based on time (optional)
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -f database/sql/assign_events.sql

   # Remove admissions not in 'database/hadm_id_list.txt'
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -f database/sql/filter_hadm.sql
   ```

## Resources

### Documentation

- [MIMIC-IV](https://mimic.mit.edu/docs/iv/modules/)
- [Pydantic](https://docs.pydantic.dev/latest/concepts/models/)
- [vLLM](https://docs.vllm.ai/en/latest/index.html)
- [PostgreSQL](https://www.postgresql.org/)

### Literature

- [CDMv1 Paper](https://www.nature.com/articles/s41591-024-03097-1)
- [Free LLM Course](https://apxml.com/courses/how-to-build-a-large-language-model)

### Videos

- [LLM Deep Dive](https://www.youtube.com/watch?v=7xTGNNLPyMI)
- [MIMIC Deep Dive](https://slideslive.com/embed/presentation/38931965)

### Code

- CDMv1: [Framework](https://github.com/paulhager/MIMIC-Clinical-Decision-Making-Framework) | [Dataset](https://github.com/paulhager/MIMIC-Clinical-Decision-Making-Dataset)
- [Official MIMIC Repository](https://github.com/MIT-LCP/mimic-code)



