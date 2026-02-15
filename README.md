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
├── cdm/                                  # Main library (reusable components)
│   ├── benchmark/                        # Benchmark data models and utilities
│   │   ├── data_models.py                # Pydantic models for cases
│   │   └── utils.py                      # Benchmark utility functions
│   ├── database/                         # Database utilities
│   │   ├── connection.py                 # DB connection management
│   │   ├── queries.py                    # Reusable SQL queries
│   │   └── utils.py                      # Database helper functions
│   ├── llms/                             # LLM agents and inference
│   │   └── agent.py                      # LLM agent implementation
│   ├── prompts/                          # Prompt templates
│   │   ├── cdm.py                        # Clinical decision-making prompts
│   │   └── full_info.py                  # Full information baseline prompts
│   ├── evaluators/                       # Pathology-specific evaluation logic 
│   │   ├── pathology_evaluator.py        # Base evaluator (shared scoring logic)
│   │   ├── appendicitis_evaluator.py     # Appendicitis-specific rules 
│   │   └── cholecystitis_evaluator.py    # Cholecystitis-specific rules    
│   │   └── diverticulitis_evaluator.py   # Diverticulitis-specific rules    
│   │   ├── pancreatitis_evaluator.py     # Pancreatitis-specific rules
│   │   └── graphing_utils.py             # Evaluation result visualization
│   └── tools/                            # Clinical tools for LLM agents
│       ├── labs.py                       # Laboratory test queries
│       ├── microbiology.py               # Microbiology test queries
│       └── physical_exam.py              # Physical examination queries
|       └── diagnosis_criteria.py         # RAG-style diagnostic criteria queries
├── configs/                              # Hydra configuration files
│   ├── benchmark/                        # Benchmark configs
│   │   ├── base.yaml                     # Base configuration
│   │   ├── cdm.yaml                      # CDM workflow config
│   │   └── full_info.yaml                # Full information baseline config
│   ├── database/                         # Database configs
│   │   └── benchmark_creation.yaml
│   └── vllm_config/                      # vLLM model configs
│       └── qwen3_4B.yaml
├── database/                             # Database setup and creation
│   ├── sql/                              # SQL scripts for DB creation
│   ├── create_benchmark.py               # Script to create benchmark JSON
│   └── README.md                         # Database schema documentation
├── scripts/                              # Executable scripts
│   ├── run_benchmark_cdm.py              # Run CDM benchmark
│   └── run_benchmark_full_info.py        # Run full information baseline
├── tests/                                # Test suite
│   ├── integration/                      # Integration tests (database, API)
│   │   └── database/                     # Database connection tests
│   └── unit/                             # Unit tests
│       └── llms/                         # LLM agent tests
│           └── test_agent.py
└── slurm/                                # Cluster job scripts
```

**Key Technologies:**
- **[uv](https://docs.astral.sh/uv/)** - Fast Python package manager
- **[Hydra](https://hydra.cc/)** - Configuration management (see `configs/`)
- **[Pydantic](https://docs.pydantic.dev/)** - Data validation and structured outputs
- **[vLLM](https://docs.vllm.ai/)** - High-performance LLM serving
- **[Loguru](https://loguru.readthedocs.io/)** - Simple, powerful logging
- **[Ruff](https://docs.astral.sh/ruff/)** - Fast Python linter and formatter
- **[pytest](https://docs.pytest.org/)** - Testing framework
- **[pre-commit](https://pre-commit.com/)** - Git hooks for code quality
- **[psycopg](https://www.psycopg.org/psycopg3/)** - PostgreSQL database adapter

**Best Practices to Follow:**
1. **Use the `cdm/` library** - Don't duplicate code, import from `cdm/`
2. **Define Pydantic models** - For all data structures (see `cdm/benchmark/models.py`)
3. **Use Hydra configs** - Store parameters in YAML files, not hardcoded
4. **Log with Loguru** - Use `logger.info()`, `logger.error()`, etc.
5. **Format with Ruff** - Run `uv run ruff format .` before committing
6. **Test your code** - Run `uv run pytest` to verify changes
7. **Use pre-commit hooks** - Install with `uv run pre-commit install` for automatic checks


## MIMIC Training

You are not allowed to use the MIMIC data before completing the following training: https://physionet.org/content/mimiciv/view-required-training/3.1/#1.

Register here: https://about.citiprogram.org
   - Click "Select Your Organization Affiliation"
   - As affiliation select "Massachusetts Institute of Technology Affiliates"
   - The remaining steps should be self-explanatory


## Workstation Setup

### Establish Connection

1. **Install [Tailscale](https://tailscale.com/kb/1347/installation)** on your local machine
2. **Connect via SSH** using VS Code's [Remote SSH extension](https://code.visualstudio.com/docs/remote/ssh):
   ```bash
   ssh <your-username>@zmaj.tail2e07d3.ts.net
   ```
   (Your supervisor will provide username and password)

### Environment Setup

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

   Create a `.env` file following [.env.template](.env.template). `.env` file is never pushed to git as it could contain personal information like API keys and password (see [.gitignore](.gitignore)).
   ```bash
   DB_NAME="mimiciv_pract"
   DB_USER="student"
   DB_PWD="student"
   ```

## Testing

This project uses **pytest** for automated testing:

```bash
# Run all tests
uv run pytest

# Run only fast tests (excludes tests marked as slow)
uv run pytest -m "not slow"

# Run tests in parallel
uv run pytest -n auto
```

**Test Organization:**
- `tests/integration/` - Integration tests (database access, API calls)
- `tests/unit/` - Unit tests for individual functions

## Pre-commit Hooks

This project uses **pre-commit** hooks to automatically check code quality:

```bash
# Install pre-commit hooks (one-time setup)
uv run pre-commit install

# Run hooks manually on all files
uv run pre-commit run --all-files
```

**Configured hooks:**
- Ruff linter/formatter - Auto-fixes code style
- YAML checker, end-of-file fixer, trailing whitespace removal
- Pytest (pre-push) - Runs fast tests before pushing

Once installed, hooks run automatically on `git commit` and `git push`.

## Development Workflow

This project uses a **branch → pull request → review → merge** workflow. Pre-commit hooks handle formatting and testing automatically.

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
