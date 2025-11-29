"""
Create benchmark dataset from MIMIC-IV database based on the CDMv1 project.

This script queries the database for each admission in hadm_id_list.txt and
extracts relevant clinical data to create a structured JSON benchmark dataset.
"""

from pathlib import Path

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
from cdm.database.utils import get_pathology_type_from_string, scrub_text


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
    ground_truth = GroundTruth(
        primary_diagnosis=ground_truth_diagnosis, treatments=ground_truth_treatments
    )

    # Data cleaning
    pathology_type = get_pathology_type_from_string(ground_truth_diagnosis)
    history_of_present_illness = scrub_text(history_of_present_illness, pathology_type)
    physical_examination = scrub_text(physical_examination, pathology_type)
    for report in radiology_reports:
        report.findings = scrub_text(report.findings, pathology_type)

    return HadmCase(
        hadm_id=hadm_id,
        demographics=demographics,
        history_of_present_illness=history_of_present_illness,
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

    # Check if --all flag is set
    process_all = cfg.get("all", False)

    # Connect to database
    conn = get_db_connection()

    try:
        cursor = conn.cursor()
        complete_cases = []

        if process_all:
            # Process all admissions
            logger.info(f"Processing all {len(hadm_ids)} admissions...")
            for hadm_id in tqdm(hadm_ids, desc="Processing admissions"):
                try:
                    case = create_hadm_case(cursor, hadm_id)
                    complete_cases.append(case)
                    logger.success(f"Added case for hadm_id={hadm_id}")

                except Exception as e:
                    logger.error(f"Failed to process hadm_id={hadm_id}: {e}")
                    # Rollback the transaction to recover from error state
                    conn.rollback()
                    continue

            if not complete_cases:
                logger.error("No admissions were successfully processed")
                return

            logger.success(
                f"Processed {len(complete_cases)} cases out of {len(hadm_ids)} admissions"
            )
        else:
            # Process each admission until we find one with complete data
            logger.info("Querying database for admissions until finding one with complete data...")
            for hadm_id in tqdm(hadm_ids, desc="Processing admissions"):
                try:
                    case = create_hadm_case(cursor, hadm_id)

                    # Check if all required fields have data
                    has_complete_data = (
                        case.demographics is not None
                        and len(case.lab_results) > 0
                        and case.physical_exam_text is not None
                        and len(case.radiology_reports) > 0
                        and len(case.microbiology_events) > 0
                        and any(r.findings for r in case.radiology_reports)
                        and case.ground_truth is not None
                        and case.ground_truth.primary_diagnosis is not None
                        and len(case.ground_truth.treatments) > 0
                    )

                    if has_complete_data:
                        complete_cases.append(case)
                        logger.success(f"Found complete case for hadm_id={hadm_id}")
                        break
                    else:
                        logger.debug(f"Incomplete data for hadm_id={hadm_id}, continuing search...")

                except Exception as e:
                    logger.error(f"Failed to process hadm_id={hadm_id}: {e}")
                    # Rollback the transaction to recover from error state
                    conn.rollback()
                    continue

            if not complete_cases:
                logger.error("No admission found with complete data for all parameters")
                return

        # Create benchmark dataset
        benchmark = BenchmarkDataset(cases=complete_cases)
        logger.success(f"Created benchmark with {len(complete_cases)} complete case(s)")

        # Export to JSON
        logger.info(f"Writing benchmark to {output_file}")
        json_output = benchmark.model_dump_json(indent=2)

        with open(output_file, "w") as f:
            f.write(json_output)

        logger.success(f"Benchmark dataset saved to {output_file}")
        if len(complete_cases) == 1:
            logger.info(f"Case hadm_id: {complete_cases[0].hadm_id}")
        else:
            logger.info(f"Cases hadm_ids: {[case.hadm_id for case in complete_cases]}")

    finally:
        cursor.close()
        conn.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    main()
