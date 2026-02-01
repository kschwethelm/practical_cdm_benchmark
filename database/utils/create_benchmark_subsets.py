#!/usr/bin/env python3
"""Create subset JSON files from benchmark datasets.

This script creates subset JSON files:
- dr_eval: 20 cases per pathology randomly selected for doctor evaluation matching the CDM v1 subset
- low_similarity: cases with history similarity < 80% or exam similarity < 80% for dataset differences analysis

The subsets are created for both the new benchmark and the CDM v1 converted benchmark.
"""

import json
from pathlib import Path

from loguru import logger

# Define the subset from CDM v1
DR_EVAL_SUBSETS = {
    "appendicitis": [
        20414022,
        20921058,
        21528320,
        22360162,
        23101737,
        23459798,
        23472780,
        23553042,
        24613821,
        25579760,
        25731420,
        26064146,
        27022057,
        27260340,
        28174867,
        28466255,
        29080331,
        29468247,
        29646721,
        29815898,
    ],
    "cholecystitis": [
        20491815,
        22023307,
        22386848,
        22825632,
        23322902,
        24642301,
        24646115,
        25643992,
        26014747,
        26146550,
        26286187,
        26354137,
        26679345,
        26983655,
        27286714,
        28342261,
        28862495,
        29573603,
        29580001,
        29723478,
    ],
    "pancreatitis": [
        20275938,
        20464014,
        20804346,
        21238215,
        21285450,
        21849575,
        22778345,
        23507935,
        23869693,
        24338433,
        24571788,
        24706695,
        25693057,
        25706907,
        25779570,
        26086670,
        26351914,
        27875265,
        29037588,
        29413431,
    ],
    "diverticulitis": [
        20348908,
        20754081,
        21177686,
        21233315,
        21793374,
        21906103,
        22631597,
        24009412,
        24188879,
        25568418,
        25682814,
        26581302,
        27371462,
        27794752,
        27989275,
        28678157,
        28967154,
        29137933,
        29270681,
        29781321,
    ],
}

# Cases with low similarity (history < 80% or exam < 80%)
LOW_SIMILARITY_CASES = [
    # History similarity < 80%
    23305064,
    24775589,
    28417762,
    29255851,
    # Exam similarity < 80%
    20521700,
    20639685,
    21292285,
    21399314,
    21902794,
    21906103,
    21948836,
    22571105,
    22727507,
    22773895,
    22855499,
    22944548,
    23352202,
    23358574,
    23611931,
    23627544,
    23680828,
    23910362,
    23977919,
    24143734,
    24188879,
    24595607,
    24797227,
    24819782,
    25033877,
    25236245,
    25559876,
    25961245,
    26130336,
    26131582,
    26339780,
    26742704,
    26765568,
    27251933,
    27562444,
    27632968,
    27906793,
    27929956,
    28272650,
    28412125,
    28414573,
    28546526,
    28627153,
    28794864,
    28865881,
    28874227,
    28930986,
    29568552,
    29775414,
    29836932,
]

OUTPUT_DIR = Path("database/output")


def load_benchmark_json(filepath: Path) -> dict:
    """Load benchmark dataset from JSON file as raw dict."""
    logger.info(f"Loading benchmark from {filepath}")
    with open(filepath) as f:
        return json.load(f)


def create_dr_eval_subset(dataset: dict) -> dict:
    """Create dr_eval subset: 20 cases per pathology for doctor evaluation matching the CDM v1 subset."""
    logger.info("Creating dr_eval subset")

    dr_eval_ids = set()
    for pathology_ids in DR_EVAL_SUBSETS.values():
        dr_eval_ids.update(pathology_ids)

    # Filter cases
    subset_cases = [case for case in dataset["cases"] if case["hadm_id"] in dr_eval_ids]

    logger.info(f"  Selected {len(subset_cases)} cases out of {len(dataset['cases'])} total")

    # Log breakdown by pathology
    pathology_counts = {}
    for case in subset_cases:
        patho = case["pathology"]
        pathology_counts[patho] = pathology_counts.get(patho, 0) + 1

    for patho, count in sorted(pathology_counts.items()):
        logger.info(f"    {patho}: {count} cases")

    return {"cases": subset_cases}


def create_low_similarity_subset(dataset: dict) -> dict:
    """Create low_similarity subset: cases with history < 80% or exam < 80% similarity."""
    logger.info("Creating low_similarity subset")

    low_sim_ids = set(LOW_SIMILARITY_CASES)

    # Filter cases
    subset_cases = [case for case in dataset["cases"] if case["hadm_id"] in low_sim_ids]

    logger.info(f"  Selected {len(subset_cases)} cases out of {len(dataset['cases'])} total")
    logger.info(f"  Expected {len(low_sim_ids)} unique IDs")

    # Log breakdown by pathology
    pathology_counts = {}
    for case in subset_cases:
        patho = case["pathology"]
        pathology_counts[patho] = pathology_counts.get(patho, 0) + 1

    for patho, count in sorted(pathology_counts.items()):
        logger.info(f"    {patho}: {count} cases")

    return {"cases": subset_cases}


def save_benchmark(dataset: dict, filepath: Path):
    """Save benchmark dataset to JSON file."""
    logger.info(f"Saving benchmark to {filepath}")
    with open(filepath, "w") as f:
        json.dump(dataset, f, indent=2)
    logger.success(f"Saved {len(dataset['cases'])} cases to {filepath}")


def main():
    """Main execution function."""
    logger.info("Starting benchmark subset creation")

    # ========== Process CDM v1 Benchmark ==========
    logger.info("\n=== Processing CDM v1 Benchmark ===")

    cdm_v1_file = OUTPUT_DIR / "benchmark_data_cdm_v1.json"
    if cdm_v1_file.exists():
        cdm_v1_dataset = load_benchmark_json(cdm_v1_file)

        # Create dr_eval subset
        cdm_v1_dr_eval = create_dr_eval_subset(cdm_v1_dataset)
        save_benchmark(cdm_v1_dr_eval, OUTPUT_DIR / "benchmark_data_cdm_v1_dr_eval.json")

        # Create low_similarity subset
        cdm_v1_low_sim = create_low_similarity_subset(cdm_v1_dataset)
        save_benchmark(cdm_v1_low_sim, OUTPUT_DIR / "benchmark_data_cdm_v1_low_similarity.json")
    else:
        logger.warning(f"CDM v1 benchmark file not found: {cdm_v1_file}")

    # ========== Process New Benchmark ==========
    logger.info("\n=== Processing New Benchmark ===")

    new_file = OUTPUT_DIR / "benchmark_data.json"
    if new_file.exists():
        new_dataset = load_benchmark_json(new_file)

        # Create dr_eval subset
        new_dr_eval = create_dr_eval_subset(new_dataset)
        save_benchmark(new_dr_eval, OUTPUT_DIR / "benchmark_data_dr_eval.json")

        # Create low_similarity subset
        new_low_sim = create_low_similarity_subset(new_dataset)
        save_benchmark(new_low_sim, OUTPUT_DIR / "benchmark_data_low_similarity.json")
    else:
        logger.warning(f"New benchmark file not found: {new_file}")

    logger.success("\n=== Subset Creation Complete ===")


if __name__ == "__main__":
    main()
