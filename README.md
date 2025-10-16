# ADLM Practical WS25/26: Clinical Decision-Making LLM Benchmark

> :warning: Complete MIMIC training BEFORE using any MIMIC data: https://physionet.org/content/mimiciv/view-required-training/3.1/#1

## Introduction

Build an **LLM-based clinical decision-making (CDM) benchmark** using real-world MIMIC-IV data. This project covers:

- Clinical reasoning workflows for LLMs (diagnosis, treatment planning)
- Structured medical data (labs, notes, diagnoses)
- Evaluation pipelines for medical AI
- Software engineering best practices for ML research

**Clinical decision-making workflow:** Information gathering → Data synthesis → Diagnostic reasoning → Treatment planning

See [scripts/demo_clinical_workflow.py](scripts/demo_clinical_workflow.py) for a basic demo.

## Code Structure

This repository follows industry best practices for Python ML projects:

```
practical_cdm_benchmark/
├── cdm/                          # Main library (reusable components)
│   ├── benchmark/                # Benchmark data models
│   │   └── models.py            # Pydantic models for cases, diagnoses
│   ├── database/                 # Database utilities
│   │   ├── connection.py        # DB connection management
│   │   └── queries.py           # Reusable SQL queries
│   └── llms/                     # LLM inference utilities
│       ├── vllm_config.py       # vLLM configuration
│       ├── vllm_inference.py    # vLLM client wrapper
│       └── data_models.py       # Pydantic models for LLM I/O
├── configs/                      # Hydra configuration files
│   ├── benchmark/               # Benchmark configs (demo.yaml)
│   ├── database/                # Database configs (benchmark_creation.yaml)
│   └── vllm_config/             # vLLM model configs (qwen3_4B.yaml)
├── database/                     # Database setup and creation
│   ├── sql/                     # SQL scripts for DB creation
│   ├── create_benchmark.py      # Script to create benchmark JSON
│   └── README.md                # Database schema documentation
├── scripts/                      # Executable scripts
│   ├── demo_clinical_workflow.py # Educational demo of clinical reasoning
│   └── vllm_test.py             # Test vLLM setup
└── slurm/                        # Cluster job scripts

```

**Key Technologies:**
- **[uv](https://docs.astral.sh/uv/)** - Fast Python package manager
- **[Hydra](https://hydra.cc/)** - Configuration management (see `configs/`)
- **[Pydantic](https://docs.pydantic.dev/)** - Data validation and structured outputs
- **[vLLM](https://docs.vllm.ai/)** - High-performance LLM serving
- **[Loguru](https://loguru.readthedocs.io/)** - Simple, powerful logging
- **[Ruff](https://docs.astral.sh/ruff/)** - Fast Python linter and formatter
- **[psycopg](https://www.psycopg.org/psycopg3/)** - PostgreSQL database adapter

**Best Practices to Follow:**
1. **Use the `cdm/` library** - Don't duplicate code, import from `cdm/`
2. **Define Pydantic models** - For all data structures (see `cdm/benchmark/models.py`)
3. **Use Hydra configs** - Store parameters in YAML files, not hardcoded
4. **Log with Loguru** - Use `logger.info()`, `logger.error()`, etc.
5. **Format with Ruff** - Run `uv run ruff format .` before committing


## Workstation Setup

### 1. Establish Connection

1. **Install [Tailscale](https://tailscale.com/kb/1347/installation)** on your local machine
2. **Connect via SSH** using VS Code's [Remote SSH extension](https://code.visualstudio.com/docs/remote/ssh):
   ```bash
   ssh <your-username>@zmaj
   ```
   (Your supervisor will provide username and password)

### 2. Environment Setup

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
   DB_NAME="mimiciv_pract"
   DB_USER="student"
   DB_PWD="student"
   ``` 

## Quick Start Guide

### 1. vLLM Setup

vLLM uses a **server-client architecture**: the server loads the model into GPU memory once and exposes an OpenAI-compatible API at `http://localhost:8000`. Your scripts act as clients sending requests to this server.

**Local PC/Workstation:**

```bash
# Terminal 1: Start server (wait for "Application startup complete")
uv run vllm serve --config configs/vllm_config/qwen3_4B.yaml

# Terminal 2: Run test script
uv run scripts/vllm_test.py
```

**Cluster (Slurm):**

```bash
# Update download_dir in configs/vllm_config/qwen3_4B.yaml to /vol/miltank/projects/LLMs
sbatch slurm/vllm_test.sbatch
```

**Note:** Model weights are stored in `/srv/llm-weights` (workstation) or `/vol/miltank/projects/LLMs` (cluster). See `download_dir` in config files.

The test script demonstrates structured JSON output with Pydantic models and OpenAI API integration.

### 2. Create Benchmark Dataset

Generate a structured JSON benchmark from database cases:

```bash
uv run database/create_benchmark.py
```

Reads admission IDs from [database/hadm_id_list.txt](database/hadm_id_list.txt), queries the database, and saves structured data to `database/output/benchmark_data.json`. Using JSON enables version control, reproducibility, and faster ML iteration.

### 3. Run Clinical Workflow Demo

Demonstrates LLM-based clinical reasoning (information gathering → diagnosis → treatment):

```bash
uv run scripts/demo_clinical_workflow.py  # Requires benchmark JSON from step 2
```

### 4. Explore the Database

The dataset contains **2,333 hospital admissions** with demographics, diagnoses, labs, medications, and clinical notes. See [database/README.md](database/README.md) for complete schema documentation.

**Query examples:**

```python
from cdm.database import get_db_connection, get_demographics, get_first_diagnosis

conn = get_db_connection()  # Uses .env configuration
cursor = conn.cursor()

# Helper functions
demographics = get_demographics(cursor, hadm_id=20001800)
diagnosis = get_first_diagnosis(cursor, hadm_id=20001800)

# Raw SQL
cursor.execute("""
    SELECT charttime, itemid, valuenum, valueuom
    FROM cdm_hosp.labevents
    WHERE hadm_id = %s
    ORDER BY charttime
""", (20001800,))
labs = cursor.fetchall()

## Development Workflow

This project uses a **branch → pull request → review → merge** workflow. Always format code with `uv run ruff format .` before committing.

**1. Create feature branch:**
```bash
git checkout main && git pull
git checkout -b feature/your-feature  # Naming: feature/, fix/, refactor/, docs/
git push -u origin feature/your-feature
```

**2. Develop and commit:**
```bash
uv run ruff format .                   # Format before committing
git add <files>                        # NEVER commit data/logs/outputs
git commit -m "feat: Description"      # Prefixes: feat/fix/refactor/docs/test
git push
```

**3. Open pull request:**
- Go to GitHub → New Pull Request → select your branch
- Write clear title and description (what, why, testing, breaking changes)
- Automated reviews: GitHub Actions + Claude Code Review check quality/security
- Address feedback, request manual review from supervisors
- Supervisors merge after approval

**GitHub Actions:** Auto-review PRs (`claude-code-review.yml`) and on-demand assistance via `@claude` mentions (`claude.yml`)

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