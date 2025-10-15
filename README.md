# ADLM Practical WS25/26: Clinical Decision-Making LLM Benchmark

> :warning: Complete MIMIC training BEFORE using any MIMIC data: https://physionet.org/content/mimiciv/view-required-training/3.1/#1

## Introduction

This practical course guides you through building an **LLM-based clinical decision-making (CDM) benchmark** using real-world data from the MIMIC-IV database. You'll learn how to:

- Design and implement clinical reasoning workflows for LLMs
- Work with structured medical data (lab results, clinical notes, diagnoses)
- Build evaluation pipelines for medical AI systems
- Apply software engineering best practices to ML research projects

### What is Clinical Decision-Making?

Clinical decision-making is the process physicians use to diagnose and treat patients. It involves:

1. **Information gathering** - Taking patient history, ordering lab tests, performing physical exams
2. **Data synthesis** - Combining multiple sources (symptoms, lab results, medical history)
3. **Diagnostic reasoning** - Generating differential diagnoses and selecting the most likely one
4. **Treatment planning** - Recommending appropriate interventions

**Example workflow:**
- Patient presents with abdominal pain → Order lab tests → Review results (elevated lipase) → Perform physical exam (epigastric tenderness) → Diagnose acute pancreatitis → Recommend treatment (NPO, IV fluids, pain management)

This benchmark evaluates how well LLMs can perform these clinical reasoning steps. See [scripts/demo_clinical_workflow.py](scripts/demo_clinical_workflow.py) for a complete implementation of this workflow.

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

## Cluster Setup

Follow kick-off lecture slides.

### Storage Configuration

**Important:** Do NOT use home directory (`~/` or `/u/home/<in-tum-username>`)

- Personal directory: `/vol/miltank/users/<username>/`
- Fast metadata storage: `/meta/users/<username>/`


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
   DB_NAME="mimiciv_pract"
   DB_USER="postgres"
   ``` 

## Quick Start Guide

### 1. Explore the Database

Our MIMIC-IV subset contains **2,333 hospital admissions** with complete clinical data. Start by understanding what data is available:

**Read the database documentation:** [database/README.md](database/README.md)
- Detailed table descriptions (diagnoses, lab results, medications, clinical notes)
- Sample SQL queries
- Data schema overview and relationships

**Database Access:**
- The database is already set up on the cluster
- Connection details are configured via `.env` file (use `.env.template` as reference)
- You can work with SQL commands or Python using `psycopg` (see [cdm/database/](cdm/database/))

**Example database queries:**
```python
from cdm.database import get_db_connection, get_demographics, get_first_diagnosis

conn = get_db_connection()
cursor = conn.cursor()

# Get patient demographics (using helper function)
demographics = get_demographics(cursor, hadm_id=20001800)

# Get primary diagnosis (using helper function)
diagnosis = get_first_diagnosis(cursor, hadm_id=20001800)

# --- Raw SQL Examples ---

# Get all lab results for a patient
cursor.execute("""
    SELECT charttime, itemid, valuenum, valueuom
    FROM labevents
    WHERE hadm_id = %s
    ORDER BY charttime
""", (20001800,))
labs = cursor.fetchall()

### 2. Create the Benchmark Dataset

Convert database cases into a structured JSON benchmark:

```bash
uv run database/create_benchmark.py
```

This script:
1. Reads all admission IDs from [database/hadm_id_list.txt](database/hadm_id_list.txt)
2. Queries the database for each case
3. Extracts demographics, diagnoses, lab results, physical exams, etc.
4. Saves to `database/output/benchmark_data.json` using Pydantic models

**Why JSON instead of direct SQL queries?**
- More portable and version-controllable
- Easier to share and reproduce results
- Simpler to load for ML training/evaluation
- Faster iteration during experiments

### 3. Run the Clinical Workflow Demo

See a complete example of how an LLM navigates a clinical case:

```bash
uv run scripts/demo_clinical_workflow.py
```

This demo shows:
- Initial patient presentation (demographics, chief complaint)
- LLM requesting diagnostic tests (labs)
- LLM performing physical examination
- Structured diagnosis and treatment output

**Note:** This requires the benchmark JSON from step 2.

### 4. Test vLLM Setup

**Understanding vLLM Server/Client Architecture:**

vLLM uses a **server-client model** to efficiently serve LLM inference:

- **Server** - Loads the LLM model into GPU memory and exposes an OpenAI-compatible API endpoint (typically `http://localhost:8000`)
- **Client** - Sends requests to the server and receives responses (your Python scripts act as clients)

**Why this architecture?**
- Load the model once, use it many times (efficient GPU memory usage)
- Multiple clients can share the same server
- Supports batching and concurrent requests for better throughput

**Test the setup:**

**On Cluster (Slurm):**
```bash
sbatch slurm/vllm_test.sbatch
```

The slurm script automatically:
- Downloads the model to `/vol/miltank/projects/LLMs` (configured in [configs/vllm_config/qwen3_4B.yaml](configs/vllm_config/qwen3_4B.yaml))
- Starts the vLLM server in the background
- Runs the client test script
- Shuts down the server after completion

**On Local PC/Workstation:**

1. **Terminal 1** - Start vLLM server:
   ```bash
   uv run vllm serve --config configs/vllm_config/qwen3_4B.yaml
   ```
   Wait until you see `"Application startup complete"` - this means the model is loaded and ready

2. **Terminal 2** - Run client script:
   ```bash
   uv run scripts/vllm_test.py
   ```
   This demonstrates structured JSON generation using Pydantic models

**What the test script shows:**
- How to connect to the vLLM server using OpenAI-compatible API
- Structured output generation with Pydantic models
- Comparison of regular vs. structured JSON responses

## Development Workflow

### Git Workflow (Collaborative Development)

This project uses a **branch → pull request → review** workflow:

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes and commit:**
   ```bash
   # Format code before committing
   uv run ruff format .

   # Stage and commit changes
   git add relevant/files.py # Only relevant code!!! NEVER add data, log files, outputs, etc.
   git commit -m "Add feature: description"
   ```

3. **Push to GitHub:**
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create a Pull Request (PR):**
   - Go to GitHub repository
   - Click "New Pull Request"
   - Select your branch
   - Add description of changes
   - Request review from supervisors

5. **Address review comments:**
   - Make requested changes
   - Push additional commits to same branch
   - PR updates automatically

6. **Merge after approval:**
   - Supervisors will merge after reviewing
   - Delete feature branch after merge

### GitHub Actions

This repository includes automated workflows:

- **Automatic Code Review** (`claude-code-review.yml`) - Automatically reviews all PRs for code quality, bugs, security, and compliance with project guidelines
- **Interactive Assistant** (`claude.yml`) - Invoke on-demand by mentioning `@claude` in issues or PR comments to execute specific tasks

### Code Quality Checks

Before submitting a PR, ensure:

```bash
# Format code
uv run ruff format .

# Check for linting errors
uv run ruff check .
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

## Appendix

### Create Database from Scratch (not needed on compute cluster)

Follow these steps to set up the database on a local machine/workstation.

#### Install PostgreSQL

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

#### Create MIMIC Database

1. Download MIMIC-IV hosp `*.csv.gz` files from https://physionet.org/content/mimiciv/3.1/

2. Load and filter hosp module:

   ```bash
   MIMIC_DIR=/opt/mimic/mimiciv/3.1/

   # Create (empty) tables
   psql -d mimiciv_pract -f database/sql/create.sql

   # Load data into tables
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -v mimic_data_dir=$MIMIC_DIR -f database/sql/hosp/load_gz.sql

   # Set primary keys, indexes, etc.
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -f database/sql/hosp/constraint.sql
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -f database/sql/hosp/index.sql

   # Assign lab and microbiology events to hadm_id based on time (optional)
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -f database/sql/hosp/assign_events.sql

   # Remove admissions not in 'database/hadm_id_list.txt'
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -f database/sql/hosp/filter_hadm.sql
   ```

3. Load and filter note module:
   ```bash
   MIMIC_DIR=/opt/mimic/mimiciv/mimic-iv-note/2.2/note/
   psql -d mimiciv_pract -f database/sql/note/create.sql
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -v mimic_data_dir=$MIMIC_DIR -f database/sql/note/load_gz.sql
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -f database/sql/note/filter_hadm.sql
   ```

4. Load note extractions:

   ```bash
   EXTRACT_DIR=/home/$USER/practical_cdm_benchmark/database/data
   psql -d mimiciv_pract -f database/sql/note_extract/create.sql
   psql -d mimiciv_pract -v ON_ERROR_STOP=1 -v mimic_data_dir=$EXTRACT_DIR -f database/sql/note_extract/load_csv.sql
   ```