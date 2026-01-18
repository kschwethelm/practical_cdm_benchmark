#!/usr/bin/env python3
"""Convert CDM v1 benchmark files to new Pydantic model format.

This script consolidates the 4 condition-specific benchmark files from CDM v1
into a single benchmark dataset using the new Pydantic models.
"""

import json
from pathlib import Path

from loguru import logger

from cdm.benchmark.data_models import (
    BenchmarkDataset,
    DetailedLabResult,
    GroundTruth,
    HadmCase,
    MicrobiologyEvent,
    Pathology,
    RadiologyReport,
    Treatment,
)

# Paths
CDM_V1_DIR = Path("/srv/student/cdm_v1")
OUTPUT_DIR = Path("database/output")
OUTPUT_FILE = OUTPUT_DIR / "benchmark_data_cdm_v1.json"

# Input files
CONDITION_FILES = [
    "appendicitis_hadm_info_first_diag.json",
    "cholecystitis_hadm_info_first_diag.json",
    "diverticulitis_hadm_info_first_diag.json",
    "pancreatitis_hadm_info_first_diag.json",
]
LAB_MAPPING_FILE = "lab_test_mapping.json"

PROBLEMATIC_CASES = [23169808, 24004035]


def load_lab_mapping(mapping_file: Path) -> dict[int, dict]:
    """Load lab test mapping and create itemid -> metadata dict."""
    logger.info(f"Loading lab test mapping from {mapping_file}")
    with open(mapping_file) as f:
        mapping_list = json.load(f)

    # Create a dict mapping itemid to test metadata
    mapping = {}
    for item in mapping_list:
        # Skip entries with missing or invalid itemid
        itemid_value = item.get("itemid")
        if itemid_value is None or (
            isinstance(itemid_value, float) and (itemid_value != itemid_value)
        ):  # Check for NaN
            continue

        itemid = int(itemid_value)
        mapping[itemid] = {
            "label": item["label"],
            "category": item.get("category"),
            "fluid": item.get("fluid"),
        }

    logger.info(f"Loaded {len(mapping)} lab test mappings")
    return mapping


def convert_lab_results(
    lab_tests: dict[str, str],
    ref_lower: dict[str, float | None],
    ref_upper: dict[str, float | None],
    lab_mapping: dict[int, dict],
) -> list[DetailedLabResult]:
    """Convert lab test data to DetailedLabResult models."""
    results = []

    for itemid_str, value in lab_tests.items():
        itemid = int(itemid_str)

        # Get test metadata from mapping
        metadata = lab_mapping.get(itemid, {})

        result = DetailedLabResult(
            itemid=itemid,
            test_name=metadata.get("label", f"Unknown Test {itemid}"),
            fluid=metadata.get("fluid"),
            category=metadata.get("category"),
            value=value if value else None,
            ref_range_lower=ref_lower.get(itemid_str),
            ref_range_upper=ref_upper.get(itemid_str),
        )
        results.append(result)

    return results


def convert_microbiology(
    micro_data: dict[str, str], micro_spec: dict[str, int]
) -> list[MicrobiologyEvent]:
    """Convert microbiology data to MicrobiologyEvent models."""
    events = []

    for test_itemid_str, comments in micro_data.items():
        test_itemid = int(test_itemid_str)
        spec_type_id = micro_spec.get(test_itemid_str)

        event = MicrobiologyEvent(
            test_itemid=test_itemid,
            test_name=None,  # Not available in CDM v1
            spec_type_desc=str(spec_type_id) if spec_type_id else None,
            organism_name=None,  # Not available in CDM v1
            comments=comments if comments else None,
            charttime=None,  # Not available in CDM v1
        )
        events.append(event)

    return events


def convert_radiology(radiology_list: list[dict]) -> list[RadiologyReport]:
    """Convert radiology data to RadiologyReport models."""
    reports = []

    for rad_dict in radiology_list:
        report = RadiologyReport(
            note_id=rad_dict.get("Note ID", ""),
            exam_name=rad_dict.get("Exam Name"),
            region=rad_dict.get("Region"),
            modality=rad_dict.get("Modality"),
            text=rad_dict.get("Report"),
        )
        reports.append(report)

    return reports


def convert_ground_truth(discharge_diagnosis: str, procedures_discharge: list[str]) -> GroundTruth:
    """Convert discharge diagnosis and procedures to GroundTruth model."""
    # Filter out None values from treatments list and convert to Treatment objects
    treatments = [
        Treatment(title=t, icd_code=None, is_coded=False)
        for t in (procedures_discharge or [])
        if t is not None
    ]

    return GroundTruth(
        primary_diagnosis=[discharge_diagnosis] if discharge_diagnosis else [],
        treatments=treatments,
    )


def convert_case(
    hadm_id: int, case_data: dict, lab_mapping: dict[int, dict], pathology: Pathology
) -> HadmCase:
    """Convert a single case from CDM v1 format to HadmCase model."""
    # Convert lab results
    lab_results = convert_lab_results(
        case_data.get("Laboratory Tests", {}),
        case_data.get("Reference Range Lower", {}),
        case_data.get("Reference Range Upper", {}),
        lab_mapping,
    )

    # Convert microbiology
    microbiology_events = convert_microbiology(
        case_data.get("Microbiology", {}), case_data.get("Microbiology Spec", {})
    )

    # Convert radiology
    radiology_reports = convert_radiology(case_data.get("Radiology", []))

    # Convert ground truth
    ground_truth = convert_ground_truth(
        case_data.get("Discharge Diagnosis", ""),
        case_data.get("Procedures Discharge", []),
    )

    # Create HadmCase
    return HadmCase(
        hadm_id=hadm_id,
        pathology=pathology,
        demographics=None,  # Not available in CDM v1 format
        patient_history=case_data.get("Patient History"),
        lab_results=lab_results,
        microbiology_events=microbiology_events,
        radiology_reports=radiology_reports,
        physical_exam_text=case_data.get("Physical Examination"),
        ground_truth=ground_truth,
    )


def main():
    """Main conversion function."""
    logger.info("Starting CDM v1 benchmark conversion")

    # Load lab test mapping
    lab_mapping = load_lab_mapping(CDM_V1_DIR / LAB_MAPPING_FILE)

    # Initialize dataset
    all_cases = []

    # Process each condition file
    for condition_file in CONDITION_FILES:
        file_path = CDM_V1_DIR / condition_file
        logger.info(f"Processing {condition_file}")

        # Extract pathology from filename (e.g., "appendicitis_hadm_info_first_diag.json" -> "appendicitis")
        pathology_name = condition_file.replace("_hadm_info_first_diag.json", "").upper()
        pathology = Pathology[pathology_name]

        with open(file_path) as f:
            condition_data = json.load(f)

        logger.info(f"  Found {len(condition_data)} cases")

        # Convert each case
        for hadm_id_str, case_data in condition_data.items():
            hadm_id = int(hadm_id_str)
            if hadm_id in PROBLEMATIC_CASES:
                # Skip known problematic case
                logger.warning(f"  Skipping problematic case hadm_id={hadm_id}")
                continue
            case = convert_case(hadm_id, case_data, lab_mapping, pathology)
            all_cases.append(case)

    # Create benchmark dataset
    dataset = BenchmarkDataset(cases=all_cases)
    logger.info(f"Total cases: {len(dataset)}")

    # Save to output file
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Saving to {OUTPUT_FILE}")

    with open(OUTPUT_FILE, "w") as f:
        f.write(dataset.model_dump_json(indent=2))

    logger.success(f"Conversion complete! Saved {len(dataset)} cases to {OUTPUT_FILE}")

    # Print summary statistics
    print("\n=== Conversion Summary ===")
    print(f"Total cases: {len(dataset)}")
    print("\nCases per condition:")
    condition_counts = {}
    for condition_file in CONDITION_FILES:
        with open(CDM_V1_DIR / condition_file) as f:
            data = json.load(f)
            condition_name = condition_file.replace("_hadm_info_first_diag.json", "")
            condition_counts[condition_name] = len(data)
            print(f"  {condition_name}: {len(data)}")

    print(f"\nOutput file: {OUTPUT_FILE}")
    print(f"File size: {OUTPUT_FILE.stat().st_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
