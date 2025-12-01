# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a clinical decision-making (CDM) benchmark project for evaluating LLMs on medical reasoning tasks using MIMIC-IV data. The project involves querying a PostgreSQL database with real clinical data, building structured benchmarks, and running LLM inference using vLLM.

**IMPORTANT:** All MIMIC data is sensitive medical information. Never commit data files, outputs, or logs containing patient information. Only commit code.

**Key Features:**
- Tool-based agent architecture for interactive clinical reasoning
- Context-based tool system for accessing case data
- Jinja2 template-based prompts with dynamic Pydantic schema injection
- Structured output validation using Pydantic models

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

# Configuration in configs/database/
# Output: database/output/benchmark_data.json
```

### Running Benchmarks
```bash
# Run CDM benchmark with tool calling (requires vLLM server)
uv run scripts/run_benchmark_cdm.py

# Run full information baseline (requires vLLM server)
uv run scripts/run_benchmark_full_info.py

# Configuration files in configs/benchmark/
# Override config: uv run scripts/run_benchmark_cdm.py num_cases=5 temperature=0.7
```

### vLLM Server/Client

**Local Development:**
```bash
# Terminal 1: Start server with a config from configs/vllm_config/
uv run vllm serve --config configs/vllm_config/<model_config>.yaml

# Terminal 2: Run benchmark scripts
uv run scripts/run_benchmark_cdm.py
```

**Cluster (Slurm):**
```bash
# Submit job (handles server startup/shutdown automatically)
sbatch slurm/<job_script>.sbatch
```

## Architecture

### Code Organization

The project uses a **library + scripts** pattern:

- **`cdm/`** - Reusable library code (import from here, don't duplicate)
  - `benchmark/` - Pydantic data models and benchmark utilities
  - `database/` - Database connection and query functions
  - `llms/` - LLM client and agent builders (build_llm, build_agent, run_agent, run_llm)
  - `prompts/` - Jinja2 templates and prompt generation utilities
  - `tools/` - Clinical information tools for agent (physical exam, labs, microbiology, radiology)
    - `context.py` - Context variable management for current case
    - `__init__.py` - AVAILABLE_TOOLS registry

- **`scripts/`** - Executable entry points (use `cdm/` library)
- **`database/`** - Database setup scripts and benchmark creation
- **`configs/`** - Hydra YAML configurations (never hardcode parameters)
  - `benchmark/` - Benchmark configurations with inheritance
  - `database/` - Database and benchmark creation configs
  - `vllm_config/` - vLLM server configurations
- **`tests/`** - Unit and integration tests
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
   - Filtered to admission IDs from `database/hadm_id_list.txt`

2. **`cdm_note`** - Clinical text notes (discharge summaries, radiology reports)

3. **`cdm_note_extract`** - Structured extractions from discharge notes

**Key relationships:**
- `patients.subject_id` → `admissions.hadm_id` → all other tables
- Dictionary tables (prefix `d_`) provide code lookups
- See [database/README.md](database/README.md) for complete schema documentation

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
- **Server** loads model into GPU memory once, exposes OpenAI-compatible API (default: `http://localhost:8000`)
- **Client** uses LangChain's ChatOpenAI to communicate with server

Benefits:
- Load model once, use many times (efficient GPU usage)
- Supports concurrent requests and batching
- Multiple scripts can share same server

**Agent-Based Clinical Decision Making:**
- **Agent** (`build_agent`) - LangChain agent with tool calling capabilities
- **Tools** - Clinical information retrieval (physical exam, labs, microbiology, radiology)
  - Tools use context variables (`get_current_case()`) to access case data
  - No case-specific tool initialization required
- **Prompts** - Jinja2 templates in `cdm/prompts/` with dynamic Pydantic schema injection
- **Tool Registry** - `AVAILABLE_TOOLS` in `cdm/tools/__init__.py` enables dynamic tool selection via config

**Context-Based Tool System:**
- `set_current_case(case)` - Set the current case before running the agent
- `get_current_case()` - Tools retrieve case data from context (no parameters needed)
- Enables agent reuse across multiple cases without rebuilding

Configuration:
- vLLM server configs in `configs/vllm_config/`
- Benchmark configs in `configs/benchmark/` (tools, temperature, etc.)
- All configs use Hydra for parameter management

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
    agent = build_agent(llm, cfg.enabled_tools)
```

**Configuration features:**
- Inheritance via `defaults` key (e.g., `defaults: [base, _self_]`)
- Override on command line: `uv run scripts/run_benchmark_cdm.py num_cases=5 temperature=0.7`
- Environment-specific configs can be created as needed

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

## Cluster Usage

**Slurm configuration:**
- Use appropriate partitions and GPU resources as configured in `slurm/` scripts
- Set HuggingFace cache to avoid filling home directory
- Refer to existing `.sbatch` files in `slurm/` for examples

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
from cdm.tools import set_current_case

# Build LLM client (connects to vLLM server)
llm = build_llm(base_url="http://localhost:8000/v1", temperature=0.0)

# Build agent once with enabled tools
agent = build_agent(llm, enabled_tools=["physical_exam", "lab", "microbiology", "radiology"])

# Set context and run agent for each case
for case in cases:
    set_current_case(case)  # Tools will access this via get_current_case()
    output: BenchmarkOutputCDM = run_agent(agent, case["history_of_present_illness"])
    print(output.final_diagnosis, output.treatment)
```

### Creating Custom Clinical Tools
```python
from langchain.tools import tool
from cdm.tools.context import get_current_case

@tool
def my_custom_tool() -> str:
    """Tool description shown to LLM."""
    case = get_current_case()  # Access current case from context
    hadm_id = case["hadm_id"]

    # Query database or perform computation
    result = perform_query(hadm_id)
    return result

# Register in cdm/tools/__init__.py
AVAILABLE_TOOLS["my_tool"] = my_custom_tool
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

### Working with Jinja2 Prompt Templates
```python
from cdm.prompts.gen_prompt_cdm import create_system_prompt, create_user_prompt
from cdm.prompts.utils import pydantic_to_prompt
from cdm.benchmark.data_models import BenchmarkOutputCDM

# Generate prompts from templates
system_prompt = create_system_prompt()  # Uses cdm/system.j2
user_prompt = create_user_prompt(patient_info)  # Uses cdm/user.j2

# Convert Pydantic model to prompt-friendly schema
schema_str = pydantic_to_prompt(BenchmarkOutputCDM)
```

## Important Reminders

- **MIMIC data is protected** - Never commit data files, outputs, or logs containing patient information
- **Always format before commit** - `uv run ruff format .` (or use pre-commit hooks)
- **Use Pydantic models** - For all data structures and LLM outputs
- **vLLM is server-client** - Start server first, then run benchmark scripts
- **Context-based tools** - Use `set_current_case()` before running agent, tools access via `get_current_case()`
- **Register new tools** - Add to `AVAILABLE_TOOLS` in `cdm/tools/__init__.py`
- **Jinja2 templates** - Prompts are in `cdm/prompts/` as `.j2` files, not hardcoded strings
