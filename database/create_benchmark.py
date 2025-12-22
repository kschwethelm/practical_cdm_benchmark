"""
Create benchmark dataset from MIMIC-IV database based on the CDMv1 project.

This script queries the database for each admission in hadm_id_list.txt and
extracts relevant clinical data to create a structured JSON benchmark dataset.
"""

from pathlib import Path

# Load environment variables from .env file BEFORE importing loguru
# This ensures LOGURU_LEVEL is available when logger is initialized
from dotenv import load_dotenv

load_dotenv()

# ruff: noqa: E402 - imports after load_dotenv() are intentional
import hydra
from loguru import logger
from omegaconf import DictConfig
from tqdm import tqdm

from cdm.benchmark.data_models import (
    BenchmarkDataset,
    Demographics,
    DetailedLabResult,
    GroundTruth,
    HadmCase,
    MicrobiologyEvent,
    RadiologyReport,
    Treatment,
)
from cdm.database.connection import get_db_connection
from cdm.database.queries import (
    get_demographics,
    get_ground_truth_diagnosis,
    get_ground_truth_treatments_coded,
    get_ground_truth_treatments_freetext,
    get_history_of_present_illness,
    get_lab_tests,
    get_microbiology_events,
    get_physical_examination,
    get_radiology_reports,
)
from cdm.database.utils import get_pathology_type_from_string, scrub_physical_exam_text, scrub_text


def load_hadm_ids(filepath: Path) -> list[int]:
    """Load hospital admission IDs from text file."""
    logger.info(f"Loading hadm_ids from {filepath}")
    with open(filepath) as f:
        hadm_ids = [int(line.strip()) for line in f if line.strip()]
    logger.success(f"Loaded {len(hadm_ids)} hadm_ids")
    return hadm_ids


def create_hadm_case(cursor, hadm_id: int) -> HadmCase:
    """Create a HadmCase by querying all relevant data for a given admission."""

    demographics_data = get_demographics(cursor, hadm_id)
    demographics = Demographics(**demographics_data) if demographics_data else None

    history_of_present_illness = get_history_of_present_illness(cursor, hadm_id)

    physical_examination = get_physical_examination(cursor, hadm_id)

    lab_data = get_lab_tests(cursor, hadm_id)
    lab_results = [DetailedLabResult(**item) for item in lab_data]

    microbiology_data = get_microbiology_events(cursor, hadm_id)
    microbiology_events = [MicrobiologyEvent(**item) for item in microbiology_data]

    radiology_reports_data = get_radiology_reports(cursor, hadm_id)
    radiology_reports = [RadiologyReport(**report) for report in radiology_reports_data]

    ground_truth_diagnosis = get_ground_truth_diagnosis(cursor, hadm_id)
    ground_truth_treatments = get_ground_truth_treatments_coded(cursor, hadm_id)
    ground_truth_treatments_free_text = get_ground_truth_treatments_freetext(cursor, hadm_id)
    ground_truth_treatments.extend(ground_truth_treatments_free_text)
    # Remove duplicates based on title while preserving order
    seen_titles = set()
    unique_treatments = []
    for treatment_dict in ground_truth_treatments:
        title = treatment_dict["title"]
        if title not in seen_titles:
            seen_titles.add(title)
            unique_treatments.append(treatment_dict)

    treatments = [Treatment(**t) for t in unique_treatments]

    ground_truth = GroundTruth(primary_diagnosis=ground_truth_diagnosis, treatments=treatments)

    # Data cleaning
    pathology_type = get_pathology_type_from_string(ground_truth_diagnosis)
    history_of_present_illness = scrub_text(history_of_present_illness, pathology_type)
    physical_examination = scrub_physical_exam_text(physical_examination)
    physical_examination = scrub_text(physical_examination, pathology_type)
    for report in radiology_reports:
        report.text = scrub_text(report.text, pathology_type)

    return HadmCase(
        hadm_id=hadm_id,
        pathology=pathology_type,
        demographics=demographics,
        patient_history=history_of_present_illness,
        lab_results=lab_results,
        microbiology_events=microbiology_events,
        radiology_reports=radiology_reports,
        physical_exam_text=physical_examination,
        ground_truth=ground_truth,
    )


@hydra.main(version_base=None, config_path="../configs/database", config_name="benchmark_creation")
def main(cfg: DictConfig):
    """Main execution function."""
    logger.info("Starting benchmark dataset creation")

    # Setup paths
    base_dir = Path(__file__).parent
    hadm_id_file = base_dir / cfg.hadm_id_file
    output_dir = base_dir / cfg.output_dir
    output_file = output_dir / cfg.output_filename

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Load admission IDs
    hadm_ids = load_hadm_ids(hadm_id_file)

    # Check if --num_cases flag is set
    num_cases = cfg.get("num_cases", None) or len(hadm_ids)

    if num_cases > len(hadm_ids):
        logger.warning(
            f"Requested num_cases ({num_cases}) exceeds available hadm_ids ({len(hadm_ids)}). "
            f"Processing all available admissions."
        )
        num_cases = len(hadm_ids)

    # Connect to database
    conn = get_db_connection()

    try:
        cursor = conn.cursor()
        cases = []

        logger.info(f"Processing {num_cases} admissions...")

        # Process admissions
        for hadm_id in tqdm(hadm_ids[:num_cases], desc="Processing admissions"):
            try:
                case = create_hadm_case(cursor, hadm_id)

                # Add case
                cases.append(case)

            except Exception as e:
                logger.error(f"Failed to process hadm_id={hadm_id}: {e}")
                # Rollback the transaction to recover from error state
                conn.rollback()
                continue

        # Check if we found any cases
        if not cases:
            raise RuntimeError("No admissions were successfully processed")

        logger.success(f"Processed {len(cases)} cases out of {len(hadm_ids)} admissions")

        # Create benchmark dataset
        benchmark = BenchmarkDataset(cases=cases)
        logger.success(f"Created benchmark with {len(cases)} case(s)")

        # Export to JSON
        logger.info(f"Writing benchmark to {output_file}")
        json_output = benchmark.model_dump_json(indent=2)

        with open(output_file, "w") as f:
            f.write(json_output)

        logger.success(f"Benchmark dataset saved to {output_file}")
        logger.info(f"Processed {len(cases)} cases. See {output_file} for details.")

    finally:
        cursor.close()
        conn.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    main()
