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
```

### Database Operations
```bash
# Create benchmark JSON from database
uv run database/create_benchmark.py

# Configuration: configs/database/benchmark_creation.yaml
# Output: database/output/benchmark_data.json
# Admission IDs: database/hadm_id_list.txt (2,333 cases)
```

### Running Scripts
```bash
# Demo clinical workflow with LLM
uv run scripts/demo_clinical_workflow.py

# Test vLLM setup (requires server running)
uv run scripts/vllm_test.py
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
  - `benchmark/models.py` - Pydantic models for clinical cases and LLM outputs
  - `database/connection.py` - Database connection utilities
  - `database/queries.py` - Reusable SQL query functions
  - `llms/vllm_inference.py` - vLLM client wrapper
  - `llms/vllm_config.py` - vLLM configuration management
  - `llms/data_models.py` - Pydantic models for LLM I/O

- **`scripts/`** - Executable scripts (use `cdm/` library)
- **`database/`** - Database setup and benchmark creation
- **`configs/`** - Hydra YAML configurations (never hardcode parameters)
- **`slurm/`** - Cluster job submission scripts

### Key Technologies

- **uv** - Python package manager (replaces pip/conda)
- **Hydra** - Configuration management via YAML files
- **Pydantic** - Data validation and structured outputs (ALL data structures should be Pydantic models)
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
from cdm.benchmark.models import HadmCase, Demographics, LabResult, DiagnosisOutput

# Example case structure
case = HadmCase(
    hadm_id=12345,
    demographics=Demographics(age=65, gender="M"),
    chief_complaints=["chest pain", "shortness of breath"],
    diagnosis="Acute myocardial infarction"
)

# LLM structured output
output = DiagnosisOutput(
    diagnosis="Community-acquired pneumonia",
    treatment=["Antibiotics", "Oxygen therapy", "IV fluids"]
)
```

### vLLM Server/Client Architecture

vLLM uses a **server-client model**:
- **Server** loads model into GPU memory once, exposes OpenAI-compatible API at `http://localhost:8000`
- **Client** sends requests via OpenAI API (see `cdm/llms/vllm_inference.py`)

Benefits:
- Load model once, use many times (efficient GPU usage)
- Supports concurrent requests and batching
- Multiple scripts can share same server

Configuration: `configs/vllm_config/qwen3_4B.yaml`
- Model download directory: `/vol/miltank/projects/LLMs` (cluster)
- Supports prefix caching and speculative decoding

### Hydra Configuration

All parameters stored in `configs/` YAML files, loaded via Hydra:

```python
import hydra
from omegaconf import DictConfig

@hydra.main(config_path="../configs/benchmark", config_name="demo", version_base="1.3")
def main(cfg: DictConfig):
    # Access config: cfg.parameter_name
    pass
```

## Development Guidelines

1. **Import from `cdm/` library** - Never duplicate code, always reuse from library
2. **Define Pydantic models** - All data structures should be Pydantic models
3. **Use Hydra configs** - Store parameters in YAML, never hardcode
4. **Log with Loguru** - Use `logger.info()`, `logger.error()`, etc.
5. **Format with Ruff** - Run `uv run ruff format .` before every commit
6. **Never commit data** - Only commit code, never data/outputs/logs

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

### LLM Inference
```python
from cdm.llms import VLLMServeClient, vLLM_Config
from cdm.llms.data_models import Chat

# Initialize client
config = vLLM_Config(...)
client = VLLMServeClient(config)

# Create chat
chat = Chat()
chat.add_user_message("What is the diagnosis?")

# Get response (async)
response = await client.generate_content(chat)
```

### Loading Benchmark Data
```python
from cdm.benchmark.models import BenchmarkDataset

# Load from JSON
dataset = BenchmarkDataset.model_validate_json(
    Path("database/output/benchmark_data.json").read_text()
)

# Access cases
for case in dataset.cases:
    print(case.hadm_id, case.demographics)
```

## Important Reminders

- **MIMIC data is protected** - Complete training at https://physionet.org/content/mimiciv/view-required-training/3.1/#1
- **Never commit patient data** - Only commit code
- **Always format before commit** - `uv run ruff format .`
- **Use Pydantic models** - For all data structures
- **vLLM is server-client** - Start server first, then run client scripts
