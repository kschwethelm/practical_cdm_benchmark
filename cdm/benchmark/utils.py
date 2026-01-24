import asyncio
import json
from pathlib import Path

from loguru import logger

from cdm.benchmark.data_models import BenchmarkDataset, HadmCase
from cdm.prompts.utils import get_diagnosis_criteria


def load_cases(benchmark_path: Path, num_cases: int = None) -> BenchmarkDataset:
    """Load cases from the benchmark dataset as Pydantic models.

    Args:
        benchmark_path: Path to the benchmark JSON file.
        num_cases: Number of cases to load. If None, load all cases.

    Returns:
        BenchmarkDataset Pydantic model
    """
    logger.info(f"Loading cases from {benchmark_path}")

    with open(benchmark_path) as f:
        data = json.load(f)

    benchmark = BenchmarkDataset(**data)
    if num_cases is not None:
        benchmark = BenchmarkDataset(cases=benchmark.cases[:num_cases])

    logger.info(f"Loaded {len(benchmark.cases)} cases")
    return benchmark


async def write_result_to_jsonl(file_path: Path, result: dict, lock: asyncio.Lock):
    """Write a single result to JSONL file with async-safe locking.

    Args:
        file_path: Path to JSONL output file
        result: Dictionary to write as JSON line
        lock: asyncio.Lock for thread-safe writing
    """
    async with lock:

        def _write():
            with file_path.open("a") as f:
                f.write(json.dumps(result) + "\n")

        await asyncio.to_thread(_write)


def add_clinical_history(case: HadmCase) -> dict:
    """Extract clinical history information from case.

    Args:
        case: HadmCase Pydantic model containing clinical history.

    Returns:
        dict: Dictionary with history of present illness and physical examination.
    """
    return {
        "patient_history": case.patient_history,
        "physical_examination": case.physical_exam_text,
    }


def add_laboratory_tests(case: HadmCase) -> dict:
    """Format laboratory test results from case.

    Args:
        case: HadmCase Pydantic model containing lab results.

    Returns:
        dict: Dictionary with formatted laboratory results string.
    """
    lab_results = ""
    for lab in case.lab_results:
        value = lab.value or "Unknown"
        ref_range_lower = lab.ref_range_lower
        ref_range_upper = lab.ref_range_upper

        # Format reference range if available
        ref_str = ""
        if ref_range_lower is not None or ref_range_upper is not None:
            ref_str = f" (ref: {ref_range_lower}-{ref_range_upper})"

        # Format category and fluid info
        category_str = ""
        if lab.category or lab.fluid:
            parts = []
            if lab.category:
                parts.append(lab.category)
            if lab.fluid:
                parts.append(lab.fluid)
            category_str = f" [{' | '.join(parts)}]"

        lab_line = f"- {lab.test_name}{category_str}: {value}{ref_str}\n"
        lab_results += lab_line

    return {"laboratory_results": lab_results}


def add_imaging_reports(case: HadmCase) -> dict:
    """Format imaging/radiology reports from case.

    Args:
        case: HadmCase Pydantic model containing radiology reports.

    Returns:
        dict: Dictionary with formatted imaging reports string.
    """
    imaging_results = ""
    for imaging in case.radiology_reports:
        exam_name = imaging.exam_name or "Unknown"
        modality = imaging.modality or ""
        region = imaging.region or ""
        reports = imaging.text or "Unknown"

        imaging_results += f"- {exam_name} ({modality}, {region})\n"
        imaging_results += f"  Reports: {reports}\n\n"

    return {"imaging_reports": imaging_results}


def add_microbiology_results(case: HadmCase) -> dict:
    """Format microbiology test results from case.

    Args:
        case: HadmCase Pydantic model containing microbiology events.

    Returns:
        dict: Dictionary with formatted microbiology results string.
    """
    micro_results = ""
    for micro in case.microbiology_events:
        test_name = micro.test_name or "Unknown"
        spec_type = micro.spec_type_desc or ""
        organism = micro.organism_name or "Unknown"
        comments = micro.comments or ""

        micro_results += f"- {test_name} ({spec_type})\n"
        micro_results += f"  Organism: {organism}\n"
        if comments:
            micro_results += f"  Comments: {comments}\n"

    return {"microbiology_results": micro_results}


def add_diagnosis_criteria() -> dict:
    """Get all diagnosis criteria for supported pathologies.

    Returns:
        dict: Dictionary with combined diagnosis criteria for all pathologies.
    """
    pathologies = ["appendicitis", "cholecystitis", "diverticulitis", "pancreatitis"]
    
    criteria_parts = []
    for pathology in pathologies:
        criteria = get_diagnosis_criteria(pathology)
        if criteria:
            criteria_parts.append(criteria)
    
    if criteria_parts:
        return {"diagnosis_criteria": "\n\n".join(criteria_parts)}
    
    return {}


def gather_all_info(case: HadmCase) -> dict:
    """Gather all clinical information by combining all data sources.

    Args:
        case: HadmCase Pydantic model containing all clinical data.

    Returns:
        dict: Dictionary with all formatted clinical information.
    """
    info = {}
    info.update(add_clinical_history(case))
    info.update(add_laboratory_tests(case))
    info.update(add_imaging_reports(case))
    info.update(add_microbiology_results(case))
    info.update(add_diagnosis_criteria())

    return info
