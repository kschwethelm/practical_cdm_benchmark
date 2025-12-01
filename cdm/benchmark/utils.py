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


def add_clinical_history(case: dict) -> dict:
    """Extract clinical history information from case.

    Args:
        case (dict): Case dictionary containing clinical history.

    Returns:
        dict: Dictionary with history of present illness and physical examination.
    """
    return {
        "history_of_present_illness": case["history_of_present_illness"],
        "physical_examination": case["physical_exam_text"],
    }


def add_laboratory_tests(case: dict) -> dict:
    """Format laboratory test results from case.

    Args:
        case (dict): Case dictionary containing lab results.

    Returns:
        dict: Dictionary with formatted laboratory results string.
    """
    lab_results = ""
    for lab in case.get("lab_results", []):
        value = lab.get("value", "Unknown")
        ref_range_lower = lab.get("ref_range_lower")
        ref_range_upper = lab.get("ref_range_upper")

        # Format reference range if available
        ref_str = ""
        if ref_range_lower is not None or ref_range_upper is not None:
            ref_str = f" (ref: {ref_range_lower}-{ref_range_upper})"

        # Format category and fluid info
        category = lab.get("category", "")
        fluid = lab.get("fluid", "")
        category_str = ""
        if category or fluid:
            parts = []
            if category:
                parts.append(category)
            if fluid:
                parts.append(fluid)
            category_str = f" [{' | '.join(parts)}]"

        lab_line = f"- {lab.get('test_name')}{category_str}: {value}{ref_str}\n"
        lab_results += lab_line

    return {"laboratory_results": lab_results}


def add_imaging_reports(case: dict) -> dict:
    """Format imaging/radiology reports from case.

    Args:
        case (dict): Case dictionary containing radiology reports.

    Returns:
        dict: Dictionary with formatted imaging reports string.
    """
    imaging_results = ""
    for imaging in case.get("radiology_reports", []):
        exam_name = imaging.get("exam_name", "Unknown")
        modality = imaging.get("modality", "")
        region = imaging.get("region", "")
        findings = imaging.get("findings", "Unknown")

        imaging_results += f"- {exam_name} ({modality}, {region})\n"
        imaging_results += f"  Findings: {findings}\n\n"

    return {"imaging_reports": imaging_results}


def add_microbiology_results(case: dict) -> dict:
    """Format microbiology test results from case.

    Args:
        case (dict): Case dictionary containing microbiology events.

    Returns:
        dict: Dictionary with formatted microbiology results string.
    """
    micro_results = ""
    for micro in case.get("microbiology_events", []):
        test_name = micro.get("test_name", "Unknown")
        spec_type = micro.get("spec_type_desc", "")
        organism = micro.get("organism_name", "Unknown")
        comments = micro.get("comments", "")

        micro_results += f"- {test_name} ({spec_type})\n"
        micro_results += f"  Organism: {organism}\n"
        if comments:
            micro_results += f"  Comments: {comments}\n"

    return {"microbiology_results": micro_results}


def gather_all_info(case: dict) -> dict:
    """Gather all clinical information by combining all data sources.

    Args:
        case (dict): Case dictionary containing all clinical data.

    Returns:
        dict: Dictionary with all formatted clinical information.
    """
    info = {}
    info.update(add_clinical_history(case))
    info.update(add_laboratory_tests(case))
    info.update(add_imaging_reports(case))
    info.update(add_microbiology_results(case))

    return info
