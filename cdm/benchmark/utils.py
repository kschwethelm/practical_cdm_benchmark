import json
from pathlib import Path

from loguru import logger


def load_cases(benchmark_path: Path, num_cases: int = None) -> list[dict]:
    """Load all cases from the benchmark dataset.

    Args:
        benchmark_path (Path): Path to the benchmark JSON file.
        num_cases (int, optional): Number of cases to load. If None, load all cases.
    """
    logger.info(f"Loading all cases from {benchmark_path}")

    with open(benchmark_path) as f:
        data = json.load(f)

    cases = data["cases"]

    if num_cases is not None:
        cases = cases[:num_cases]

    return cases
