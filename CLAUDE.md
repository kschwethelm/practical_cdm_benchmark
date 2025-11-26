# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a clinical decision-making (CDM) benchmark project for evaluating LLMs on medical reasoning tasks using MIMIC-IV data. The project involves querying a PostgreSQL database with real clinical data, building structured benchmarks, and running LLM inference using vLLM.

**IMPORTANT:** All MIMIC data is sensitive medical information. Never commit data files, outputs, or logs containing patient information. Only commit code.

## Development Commands

### Environment Setup
```bash
# Install dependencies and create virtual environment
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### Code Quality
```bash
# Format code (ALWAYS run before committing)
uv run ruff format .

# Check for linting errors
uv run ruff check .

# Run tests
uv run pytest                    # All tests
uv run pytest -m "not slow"      # Fast tests only
uv run pytest -n auto            # Parallel execution

# Pre-commit hooks (auto-format, lint, test)
uv run pre-commit install        # One-time setup
uv run pre-commit run --all-files  # Manual check
```

### Database Operations
```bash
# Create benchmark JSON from database
uv run database/create_benchmark.py

# Configuration: configs/database/benchmark_creation.yaml
# Output: database/output/benchmark_data.json
# Admission IDs: database/hadm_id_list.txt (2,333 cases)
```

### Running Benchmarks
```bash
# Run CDM benchmark with tool calling (requires vLLM server + benchmark JSON)
uv run scripts/run_benchmark_cdm.py

# Run full information baseline (requires vLLM server + benchmark JSON)
uv run scripts/run_benchmark_full_info.py

# Configuration files: configs/benchmark/cdm.yaml and configs/benchmark/full_info.yaml
```

### vLLM Server/Client

**Local Development:**
```bash
# Terminal 1: Start server
uv run vllm serve --config configs/vllm_config/qwen3_4B.yaml
# Wait for "Application startup complete"

# Terminal 2: Run client scripts
uv run scripts/vllm_test.py
```

**Cluster (Slurm):**
```bash
# Submit job (handles server startup/shutdown automatically)
sbatch slurm/vllm_test.sbatch
```

## Architecture

### Code Organization

The project uses a **library + scripts** pattern:

- **`cdm/`** - Reusable library code (import from here, don't duplicate)
  - `benchmark/data_models.py` - Pydantic models for LLM outputs (BenchmarkOutputCDM, BenchmarkOutputFullInfo)
  - `benchmark/utils.py` - Benchmark utility functions (load_cases, etc.)
  - `database/connection.py` - Database connection utilities
  - `database/queries.py` - Reusable SQL query functions
  - `database/utils.py` - Database helper functions
  - `llms/agent.py` - LangChain agent with tool calling (build_agent, run_agent, build_llm)
  - `prompts/cdm.py` - Clinical decision-making prompts (tool-calling workflow)
  - `prompts/full_info.py` - Full information baseline prompts
  - `tools/` - Clinical information tools for agent
    - `physical_exam.py` - Physical examination queries
    - `labs.py` - Laboratory test queries
    - `microbiology.py` - Microbiology test queries
    - `__init__.py` - AVAILABLE_TOOLS registry

- **`scripts/`** - Executable scripts (use `cdm/` library)
  - `run_benchmark_cdm.py` - Run CDM benchmark with tool calling
  - `run_benchmark_full_info.py` - Run full information baseline
- **`database/`** - Database setup and benchmark creation
- **`configs/`** - Hydra YAML configurations (never hardcode parameters)
  - `benchmark/base.yaml` - Base configuration (shared settings)
  - `benchmark/cdm.yaml` - CDM workflow configuration
  - `benchmark/full_info.yaml` - Full information baseline configuration
- **`slurm/`** - Cluster job submission scripts

### Key Technologies

- **uv** - Python package manager (replaces pip/conda)
- **Hydra** - Configuration management via YAML files
- **Pydantic** - Data validation and structured outputs (ALL data structures should be Pydantic models)
- **LangChain** - Agent framework with tool calling for clinical decision-making workflows
- **vLLM** - High-performance LLM serving (server-client architecture)
- **psycopg** - PostgreSQL adapter for database queries
- **Loguru** - Logging (`from loguru import logger`)
- **Ruff** - Fast linting and formatting

### Database Architecture

The PostgreSQL database contains 3 schemas:

1. **`cdm_hosp`** - Hospital data (diagnoses, labs, medications, procedures)
   - Key tables: `admissions`, `patients`, `diagnoses_icd`, `labevents`, `prescriptions`
   - All filtered to 2,333 admissions from `database/hadm_id_list.txt`

2. **`cdm_note`** - Clinical text notes
   - `discharge` - Discharge summaries (1 per admission)
   - `radiology` - Radiology reports (~2.3 per admission)

3. **`cdm_note_extract`** - Structured extractions from discharge notes
   - Tables: `chief_complaint`, `physical_exam`, `past_medical_history`, `discharge_diagnosis`, etc.

**Key relationships:**
- `patients.subject_id` → `admissions.hadm_id` → all other tables
- Dictionary tables (prefix `d_`) provide code lookups (not filtered)
- See `database/README.md` for complete schema documentation

### Database Connection

```python
from cdm.database import get_db_connection, db_cursor

# Direct connection
conn = get_db_connection()  # Reads .env for DB_NAME, DB_USER
cursor = conn.cursor()

# Context manager (auto-commit/rollback)
with db_cursor() as cur:
    cur.execute("SELECT * FROM cdm_hosp.admissions WHERE hadm_id = %s", (12345,))
```

Environment variables (`.env` file):
```
DB_NAME="mimiciv_pract"
DB_USER="postgres"
```

### Pydantic Models

All data structures use Pydantic for validation:

```python
from cdm.benchmark.data_models import BenchmarkOutputCDM, BenchmarkOutputFullInfo

# CDM workflow output (with tool calling)
output = BenchmarkOutputCDM(
    thought="Based on fever, cough, and chest X-ray findings...",
    final_diagnosis="Community-acquired pneumonia",
    treatment=["Antibiotics", "Oxygen therapy", "IV fluids"]
)

# Full information baseline output
output = BenchmarkOutputFullInfo(
    diagnosis="Community-acquired pneumonia"
)
```

### LLM Architecture

**vLLM Server-Client Model:**
- **Server** loads model into GPU memory once, exposes OpenAI-compatible API at `http://localhost:8000`
- **Client** uses LangChain's ChatOpenAI to communicate with server (see `cdm/llms/agent.py`)

Benefits:
- Load model once, use many times (efficient GPU usage)
- Supports concurrent requests and batching
- Multiple scripts can share same server

**Agent-Based Clinical Decision Making:**
- **Agent** (`build_agent`) - LangChain agent with tool calling capabilities
- **Tools** - Clinical information retrieval (physical exam, labs, microbiology)
- **Prompts** - System and user prompts for CDM workflow (`cdm/prompts/cdm.py`)
- Tool registry in `cdm/tools/__init__.py` allows dynamic tool selection via config

Configuration:
- vLLM: `configs/vllm_config/qwen3_4B.yaml`
- Benchmark: `configs/benchmark/cdm.yaml` (tools, temperature, etc.)
- Model download directory: `/vol/miltank/projects/LLMs` (cluster)

### Hydra Configuration

All parameters stored in `configs/` YAML files, loaded via Hydra:

```python
import hydra
from omegaconf import DictConfig

@hydra.main(version_base=None, config_path="../configs/benchmark", config_name="cdm")
def main(cfg: DictConfig):
    # Access config parameters
    cases = load_cases(cfg.benchmark_data_path, cfg.num_cases)
    llm = build_llm(cfg.base_url, cfg.temperature)
    agent = build_agent(case, llm, cfg.enabled_tools)
```

**Configuration inheritance:**
- `configs/benchmark/cdm.yaml` inherits from `base.yaml` using `defaults: [base, _self_]`
- Override configs on command line: `uv run scripts/run_benchmark_cdm.py num_cases=5 temperature=0.7`

## Development Guidelines

1. **Import from `cdm/` library** - Never duplicate code, always reuse from library
2. **Define Pydantic models** - All data structures should be Pydantic models (see `cdm/benchmark/data_models.py`)
3. **Use Hydra configs** - Store parameters in YAML, never hardcode (see `configs/benchmark/`)
4. **Register new tools** - Add to `AVAILABLE_TOOLS` in `cdm/tools/__init__.py`
5. **Log with Loguru** - Use `logger.info()`, `logger.error()`, etc.
6. **Format with Ruff** - Run `uv run ruff format .` before every commit (or use pre-commit hooks)
7. **Run tests** - Use `uv run pytest` to verify changes
8. **Never commit data** - Only commit code, never data/outputs/logs

### Testing

Tests are located in `tests/integration/` and `tests/unit/`. Pre-commit hooks automatically run fast tests on push.

### Pre-commit Hooks

Once installed (`uv run pre-commit install`), hooks run automatically on commit/push:
- Ruff formatter/linter - Auto-fixes code style
- YAML checker, end-of-file fixer, trailing whitespace removal
- Pytest (pre-push) - Runs fast tests before pushing

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Format before committing
uv run ruff format .

# Commit only relevant code (NEVER data/logs/outputs)
git add relevant_files.py
git commit -m "Add feature: description"

# Push and create PR
git push origin feature/your-feature-name
```

## Cluster-Specific Notes

**Storage locations:**
- Personal directory: `/vol/miltank/users/<username>/`
- Fast metadata storage: `/meta/users/<username>/`
- LLM models: `/vol/miltank/projects/LLMs`
- **NEVER use home directory (`~/`)**

**Slurm configuration:**
- Partitions: `universe`, `asteroids`
- GPU jobs: `#SBATCH --gres=gpu:1`
- Set HuggingFace cache: `export HF_HOME=/vol/miltank/users/$USER/.cache/huggingface`
- Example: `slurm/vllm_test.sbatch`

## Common Patterns

### Querying Database
```python
from cdm.database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

# Get demographics
cursor.execute("""
    SELECT p.gender, p.anchor_age, a.race
    FROM cdm_hosp.admissions a
    JOIN cdm_hosp.patients p ON a.subject_id = p.subject_id
    WHERE a.hadm_id = %s
""", (hadm_id,))
```

### Building and Running LLM Agent
```python
from cdm.llms.agent import build_llm, build_agent, run_agent
from cdm.benchmark.data_models import BenchmarkOutputCDM

# Build LLM client (connects to vLLM server)
llm = build_llm(base_url="http://localhost:8000/v1", temperature=0.0)

# Build agent with tools
agent = build_agent(
    case=case_dict,
    llm=llm,
    enabled_tools=["physical_exam", "lab", "microbiology"]
)

# Run agent with patient information
output: BenchmarkOutputCDM = run_agent(agent, patient_info)
print(output.final_diagnosis, output.treatment)
```

### Creating Custom Clinical Tools
```python
from langchain_core.tools import tool

@tool
def create_my_tool(case: dict):
    """Query custom clinical information."""
    hadm_id = case["hadm_id"]

    def tool_function(query: str) -> str:
        """Tool description for LLM."""
        # Query database or perform computation
        return result

    return tool_function

# Register in cdm/tools/__init__.py
AVAILABLE_TOOLS["my_tool"] = create_my_tool
```

### Loading Benchmark Data
```python
from cdm.benchmark.utils import load_cases

# Load cases from JSON
cases = load_cases("database/output/benchmark_data.json", num_cases=10)

# Access case data
for case in cases:
    print(case["hadm_id"], case["history_of_present_illness"])
    print(case["ground_truth"]["primary_diagnosis"])
```

## Important Reminders

- **MIMIC data is protected** - Complete training at https://physionet.org/content/mimiciv/view-required-training/3.1/#1
- **Never commit patient data** - Only commit code
- **Always format before commit** - `uv run ruff format .`
- **Use Pydantic models** - For all data structures (see `cdm/benchmark/data_models.py`)
- **vLLM is server-client** - Start server first (`uv run vllm serve --config ...`), then run benchmark scripts
- **Agent architecture** - Use LangChain agents with tool calling for CDM workflows
- **Register new tools** - Add to `AVAILABLE_TOOLS` in `cdm/tools/__init__.py`
