"""
Create benchmark dataset from MIMIC-IV database.

This script queries the database for each admission in hadm_id_list.txt and
extracts relevant clinical data to create a structured JSON benchmark dataset.
"""

from pathlib import Path

import hydra
from loguru import logger
from omegaconf import DictConfig
from tqdm import tqdm

from cdm.benchmark.models import (
    BenchmarkDataset,
    Demographics,
    HadmCase,
    LabResult,
    MicrobiologyResult,
    PastMedicalHistory,
    PhysicalExam,
)
from cdm.database.connection import get_db_connection
from cdm.database.queries import (
    get_all_past_medical_history,
    get_demographics,
    get_first_diagnosis,
    get_first_lab_result,
    get_first_microbiology_result,
    get_first_physical_exam,
    get_presenting_chief_complaints,
)


def load_hadm_ids(filepath: Path) -> list[int]:
    """Load hospital admission IDs from text file."""
    logger.info(f"Loading hadm_ids from {filepath}")
    with open(filepath) as f:
        hadm_ids = [int(line.strip()) for line in f if line.strip()]
    logger.success(f"Loaded {len(hadm_ids)} hadm_ids")
    return hadm_ids


def create_hadm_case(cursor, hadm_id: int) -> HadmCase:
    """Create a HadmCase by querying all relevant data for a given admission."""

    # Get demographics
    demographics_data = get_demographics(cursor, hadm_id)
    demographics = Demographics(**demographics_data) if demographics_data else None

    # Get first lab result
    lab_data = get_first_lab_result(cursor, hadm_id)
    first_lab_result = LabResult(**lab_data) if lab_data else None

    # Get first microbiology result
    micro_data = get_first_microbiology_result(cursor, hadm_id)
    first_microbiology_result = MicrobiologyResult(**micro_data) if micro_data else None

    # Get all chief complaints from 'chief_complaint' category
    chief_complaints = get_presenting_chief_complaints(cursor, hadm_id)

    # Get first primary diagnosis
    diagnosis = get_first_diagnosis(cursor, hadm_id)

    # Get all past medical history
    pmh_data = get_all_past_medical_history(cursor, hadm_id)
    past_medical_history = [PastMedicalHistory(**item) for item in pmh_data]

    # Get first physical exam
    pe_data = get_first_physical_exam(cursor, hadm_id)
    physical_exam = PhysicalExam(**pe_data) if pe_data else None

    return HadmCase(
        hadm_id=hadm_id,
        demographics=demographics,
        first_lab_result=first_lab_result,
        first_microbiology_result=first_microbiology_result,
        chief_complaints=chief_complaints,
        diagnosis=diagnosis,
        past_medical_history=past_medical_history,
        physical_exam=physical_exam,
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

    # Connect to database
    conn = get_db_connection()

    try:
        cursor = conn.cursor()
        cases = []

        # Process each admission
        logger.info("Querying database for each admission...")
        for hadm_id in tqdm(hadm_ids, desc="Processing admissions"):
            try:
                case = create_hadm_case(cursor, hadm_id)
                cases.append(case)
            except Exception as e:
                logger.error(f"Failed to process hadm_id={hadm_id}: {e}")
                continue

        # Create benchmark dataset
        benchmark = BenchmarkDataset(cases=cases)
        logger.success(f"Created benchmark with {len(cases)} cases")

        # Export to JSON
        logger.info(f"Writing benchmark to {output_file}")
        json_output = benchmark.model_dump_json(indent=2)

        with open(output_file, "w") as f:
            f.write(json_output)

        logger.success(f"Benchmark dataset saved to {output_file}")
        logger.info(f"Total cases: {len(cases)}")

    finally:
        cursor.close()
        conn.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    main()
