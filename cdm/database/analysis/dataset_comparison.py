"""
Simple dataset comparison function for CDMv1 validation

Usage:
    # From Python:
    from cdm.database.analysis.dataset_comparison import compare_datasets
    results = compare_datasets('database/output/benchmark_data.json')

    # From terminal:
    uv run cdm/database/analysis/dataset_comparison.py database/output/benchmark_data.json
    uv run cdm/database/analysis/dataset_comparison.py database/output/benchmark_data.json --output my_report.txt
"""

import argparse
import json
from pathlib import Path


def compare_datasets(new_dataset_path, cdm_v1_dir="/srv/student/cdm_v1", output_file=None):
    """
    Compare new dataset with original CDMv1 dataset files.

    Text similarity is calculated using Jaccard similarity: the size of the intersection
    divided by the size of the union of word sets (after lowercasing and basic tokenization).

    Args:
        new_dataset_path: Path to new benchmark_data.json
        cdm_v1_dir: Directory containing CDMv1 files (pancreatitis, appendicitis, etc.)
        output_file: Optional path to save summary report (default: auto-generated next to dataset)

    Returns:
        dict: Comparison results with match statistics

    Raises:
        FileNotFoundError: If dataset or CDMv1 files are not found
        json.JSONDecodeError: If JSON files are malformed
    """
    # Load new dataset
    try:
        with open(new_dataset_path) as f:
            new_data = json.load(f)
    except FileNotFoundError as err:
        raise FileNotFoundError(f"Dataset file not found: {new_dataset_path}") from err
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in dataset file: {e.msg}", e.doc, e.pos) from e

    # Load all CDMv1 dataset files
    cdm_v1_data = {}
    for diagnosis in ["pancreatitis", "appendicitis", "cholecystitis", "diverticulitis"]:
        file_path = Path(cdm_v1_dir) / f"{diagnosis}_hadm_info_first_diag.json"
        if file_path.exists():
            try:
                with open(file_path) as f:
                    cdm_v1_data.update(json.load(f))
            except json.JSONDecodeError as e:
                print(f"Warning: Invalid JSON in {file_path}: {e}")
                continue

    results = []

    # Compare each case in new dataset
    for case in new_data["cases"]:
        hadm_id = str(case["hadm_id"])

        # Find matching case in CDMv1
        if hadm_id not in cdm_v1_data:
            results.append(
                {
                    "hadm_id": hadm_id,
                    "found": False,
                    "diagnosis": case.get("ground_truth", {}).get("primary_diagnosis", []),
                }
            )
            continue

        cdm_case = cdm_v1_data[hadm_id]

        # Compare important fields
        comparison = {
            "hadm_id": hadm_id,
            "found": True,
            "diagnosis": case.get("ground_truth", {}).get("primary_diagnosis", []),
        }

        # 1. Patient History (text similarity)
        cdm_history = cdm_case.get("Patient History", "").lower().split()
        new_history = case.get("patient_history", "").lower().split()
        if cdm_history and new_history:
            overlap = len(set(cdm_history) & set(new_history))
            similarity = overlap / max(len(set(cdm_history)), len(set(new_history)))
            comparison["history_similarity"] = round(similarity, 2)
        else:
            comparison["history_similarity"] = 0.0

        # 2. Physical Exam (text similarity)
        cdm_exam = cdm_case.get("Physical Examination", "").lower().split()
        new_exam = case.get("physical_exam_text", "").lower().split()
        if cdm_exam and new_exam:
            overlap = len(set(cdm_exam) & set(new_exam))
            similarity = overlap / max(len(set(cdm_exam)), len(set(new_exam)))
            comparison["exam_similarity"] = round(similarity, 2)
        else:
            comparison["exam_similarity"] = 0.0

        # 3. Lab Tests (detailed comparison)
        cdm_labs = cdm_case.get("Laboratory Tests", {})
        new_labs_list = case.get("lab_results", [])

        # Compare by itemids
        cdm_itemids = set(cdm_labs.keys())
        new_itemids = {str(lab["itemid"]) for lab in new_labs_list if lab.get("itemid")}

        comparison["cdm_lab_count"] = len(cdm_itemids)
        comparison["new_lab_count"] = len(new_itemids)
        comparison["lab_overlap"] = len(cdm_itemids & new_itemids)
        comparison["lab_missing"] = len(cdm_itemids - new_itemids)
        comparison["lab_extra"] = len(new_itemids - cdm_itemids)

        # Store the actual missing/extra itemids for debugging
        if cdm_itemids - new_itemids:
            comparison["lab_missing_itemids"] = list(cdm_itemids - new_itemids)
        if new_itemids - cdm_itemids:
            comparison["lab_extra_itemids"] = list(new_itemids - cdm_itemids)

        # Check if itemids are present
        new_labs_with_itemid = [lab for lab in new_labs_list if "itemid" in lab and lab["itemid"]]
        comparison["new_labs_have_itemid"] = len(new_labs_with_itemid)

        # Compare lab values for matching tests by itemid
        lab_value_matches = 0
        lab_value_mismatches = 0
        lab_value_mismatch_details = []

        # Create lookup for new labs by itemid
        new_labs_by_itemid = {}
        for lab in new_labs_list:
            if lab.get("itemid"):
                new_labs_by_itemid[str(lab["itemid"])] = lab

        for itemid, cdm_value in cdm_labs.items():
            new_lab = new_labs_by_itemid.get(itemid)
            if new_lab and new_lab.get("value"):
                # Normalize values for comparison
                cdm_val_norm = str(cdm_value).strip().lower()
                new_val_norm = str(new_lab["value"]).strip().lower()

                # Try to parse as numeric to handle formatting differences like "10.0" vs "10"
                try:
                    cdm_num = float(cdm_val_norm.split()[0])
                    new_num = float(new_val_norm.split()[0])
                    # Also compare units if present
                    cdm_parts = cdm_val_norm.split()
                    new_parts = new_val_norm.split()
                    units_match = (
                        len(cdm_parts) == 1
                        or len(new_parts) == 1
                        or " ".join(cdm_parts[1:]) == " ".join(new_parts[1:])
                    )
                    if abs(cdm_num - new_num) < 0.001 and units_match:
                        lab_value_matches += 1
                    else:
                        lab_value_mismatches += 1
                        lab_value_mismatch_details.append(
                            {
                                "itemid": itemid,
                                "cdm_value": cdm_value,
                                "new_value": new_lab["value"],
                            }
                        )
                except (ValueError, IndexError):
                    # Not numeric, do string comparison
                    if cdm_val_norm == new_val_norm:
                        lab_value_matches += 1
                    else:
                        lab_value_mismatches += 1
                        lab_value_mismatch_details.append(
                            {
                                "itemid": itemid,
                                "cdm_value": cdm_value,
                                "new_value": new_lab["value"],
                            }
                        )

        comparison["lab_value_matches"] = lab_value_matches
        comparison["lab_value_mismatches"] = lab_value_mismatches
        if lab_value_mismatch_details:
            comparison["lab_value_mismatch_details"] = lab_value_mismatch_details

        # 4. Radiology (detailed comparison)
        cdm_rad_reports = cdm_case.get("Radiology", [])
        new_rad_reports = case.get("radiology_reports", [])

        comparison["cdm_radiology_count"] = len(cdm_rad_reports)
        comparison["new_radiology_count"] = len(new_rad_reports)
        comparison["radiology_match"] = len(cdm_rad_reports) == len(new_rad_reports)

        # Check for note_id field
        new_rad_with_note_id = [r for r in new_rad_reports if "note_id" in r and r["note_id"]]
        comparison["new_radiology_have_note_id"] = len(new_rad_with_note_id)

        # Compare note IDs
        cdm_exams = {str(r.get("Note ID", "")) for r in cdm_rad_reports if r.get("Note ID")}
        new_exams = {str(r.get("note_id", "")) for r in new_rad_reports if r.get("note_id")}

        if cdm_exams or new_exams:
            comparison["radiology_exam_overlap"] = len(cdm_exams & new_exams)
            comparison["radiology_exam_missing"] = len(cdm_exams - new_exams)
            comparison["radiology_exam_extra"] = len(new_exams - cdm_exams)
            # Store the actual missing/extra exam names for debugging
            if cdm_exams - new_exams:
                comparison["radiology_missing_exams"] = list(cdm_exams - new_exams)
            if new_exams - cdm_exams:
                comparison["radiology_extra_exams"] = list(new_exams - cdm_exams)

        # Compare modalities
        cdm_modalities = {
            r.get("Modality", "").strip().upper() for r in cdm_rad_reports if r.get("Modality")
        }
        new_modalities = {
            r.get("modality", "").strip().upper() for r in new_rad_reports if r.get("modality")
        }

        if cdm_modalities or new_modalities:
            comparison["radiology_modality_overlap"] = len(cdm_modalities & new_modalities)

        # Compare regions
        cdm_regions = {
            r.get("Region", "").strip().lower() for r in cdm_rad_reports if r.get("Region")
        }
        new_regions = {
            r.get("region", "").strip().lower() for r in new_rad_reports if r.get("region")
        }

        if cdm_regions or new_regions:
            comparison["radiology_region_overlap"] = len(cdm_regions & new_regions)

        # Compare text similarity
        if cdm_rad_reports and new_rad_reports:
            # Create lookup for new reports by note_id
            new_reports_by_id = {}
            for new_report in new_rad_reports:
                if new_report.get("note_id"):
                    new_reports_by_id[str(new_report["note_id"])] = new_report

            # Calculate text similarity for matching note_ids
            text_similarities = []
            for cdm_report in cdm_rad_reports:
                cdm_note_id = str(cdm_report.get("Note ID", ""))
                if cdm_note_id and cdm_note_id in new_reports_by_id:
                    cdm_text = cdm_report.get("Report", "").lower().split()
                    new_text = new_reports_by_id[cdm_note_id].get("text", "").lower().split()
                    if cdm_text and new_text:
                        overlap = len(set(cdm_text) & set(new_text))
                        similarity = overlap / max(len(set(cdm_text)), len(set(new_text)))
                        text_similarities.append(similarity)

            if text_similarities:
                comparison["radiology_text_similarity"] = round(
                    sum(text_similarities) / len(text_similarities), 2
                )

        # 5. Microbiology (detailed comparison)
        cdm_micro = cdm_case.get("Microbiology", {})
        new_micro_events = case.get("microbiology_events", [])

        # Count non-empty results (check both organism_name and comments)
        cdm_micro_count = sum(1 for v in cdm_micro.values() if v and v.strip())
        new_micro_count = len(
            [e for e in new_micro_events if e.get("organism_name") or e.get("comments")]
        )

        comparison["cdm_micro_count"] = cdm_micro_count
        comparison["new_micro_count"] = new_micro_count
        comparison["micro_match"] = cdm_micro_count == new_micro_count

        # Check for test_itemid field
        new_micro_with_itemid = [
            e for e in new_micro_events if "test_itemid" in e and e["test_itemid"]
        ]
        comparison["new_micro_have_itemid"] = len(new_micro_with_itemid)

        # Compare results (organism names or comments)
        cdm_results = set()
        for result in cdm_micro.values():
            if result and result.strip():
                # Split by comma, normalize and sort to handle different ordering
                parts = [p.strip().lower() for p in result.split(",")]
                normalized = ", ".join(sorted(parts))
                cdm_results.add(normalized)

        new_results = set()
        for event in new_micro_events:
            # Use organism_name if available, otherwise use comments
            org = event.get("organism_name", "")
            comm = event.get("comments", "")

            # Add both org_name and comments separately if they exist
            if org and org.strip():
                parts = [p.strip().lower() for p in org.split(",")]
                normalized = ", ".join(sorted(parts))
                new_results.add(normalized)
            if comm and comm.strip():
                parts = [p.strip().lower() for p in comm.split(",")]
                normalized = ", ".join(sorted(parts))
                new_results.add(normalized)

        if cdm_results or new_results:
            # Calculate overlaps considering substring matches for comments
            overlap_count = 0
            missing_results = set()

            for cdm_result in cdm_results:
                found = False
                # Check exact match first
                if cdm_result in new_results:
                    overlap_count += 1
                    found = True
                else:
                    # Check if CDM result is contained in any new result (for comments)
                    for new_result in new_results:
                        if cdm_result in new_result or new_result in cdm_result:
                            overlap_count += 1
                            found = True
                            break

                if not found:
                    missing_results.add(cdm_result)

            # Calculate extra results
            extra_results = set()
            for new_result in new_results:
                found = False
                for cdm_result in cdm_results:
                    if (
                        new_result == cdm_result
                        or cdm_result in new_result
                        or new_result in cdm_result
                    ):
                        found = True
                        break
                if not found:
                    extra_results.add(new_result)

            comparison["micro_organism_overlap"] = overlap_count
            comparison["micro_organism_missing"] = len(missing_results)
            comparison["micro_organism_extra"] = len(extra_results)
            # Store the actual missing/extra values for debugging
            if missing_results:
                comparison["micro_missing_values"] = list(missing_results)
            if extra_results:
                comparison["micro_extra_values"] = list(extra_results)
            if new_results - cdm_results:
                comparison["micro_extra_values"] = list(new_results - cdm_results)

        # 6. Diagnosis
        cdm_diag = cdm_case.get("Discharge Diagnosis", "")
        new_diagnoses = case.get("ground_truth", {}).get("primary_diagnosis", [])

        # Normalize CDM diagnosis
        cdm_diag_normalized = cdm_diag.replace("___", "")
        cdm_diag_normalized = " ".join(cdm_diag_normalized.split()).strip().lower()

        # Check if any of the new diagnoses match the CDM diagnosis
        diagnosis_match = False
        if new_diagnoses:
            for new_diag in new_diagnoses:
                new_diag_normalized = new_diag.replace("[REDACTED]", "")
                new_diag_normalized = " ".join(new_diag_normalized.split()).strip().lower()

                if (
                    new_diag_normalized in cdm_diag_normalized
                    or cdm_diag_normalized in new_diag_normalized
                ):
                    diagnosis_match = True
                    break

        comparison["diagnosis_in_discharge"] = diagnosis_match

        # Count diagnoses
        comparison["num_diagnoses"] = len(new_diagnoses)

        # 7. Demographics comparison
        new_demo = case.get("demographics", {})
        if new_demo:
            comparison["has_demographics"] = True
            comparison["has_age"] = "age" in new_demo and new_demo["age"] is not None
            comparison["has_gender"] = "gender" in new_demo and new_demo["gender"] is not None
        else:
            comparison["has_demographics"] = False

        # 8. Procedures/Treatments comparison
        cdm_procedures = set()

        # Collect from ICD9 titles
        for proc in cdm_case.get("Procedures ICD9 Title", []):
            if proc and proc.strip():
                cdm_procedures.add(proc.strip().lower())

        # Collect from ICD10 titles
        for proc in cdm_case.get("Procedures ICD10 Title", []):
            if proc and proc.strip():
                cdm_procedures.add(proc.strip().lower())

        # Collect from discharge procedures
        discharge_procs = cdm_case.get("Procedures Discharge", [])
        if isinstance(discharge_procs, str):
            if discharge_procs.strip():
                cdm_procedures.add(discharge_procs.strip().lower())
        elif isinstance(discharge_procs, list):
            for proc in discharge_procs:
                if proc and proc.strip():
                    cdm_procedures.add(proc.strip().lower())

        new_treatments = set()
        for treatment in case.get("ground_truth", {}).get("treatments", []):
            if treatment:
                if isinstance(treatment, dict):
                    treatment_text = treatment.get("title", "")
                else:
                    treatment_text = treatment
                if treatment_text and treatment_text.strip():
                    new_treatments.add(treatment_text.strip().lower())

        comparison["cdm_procedures_count"] = len(cdm_procedures)
        comparison["new_treatments_count"] = len(new_treatments)

        # Check for partial matches (procedures often have different wording)
        if cdm_procedures and new_treatments:
            exact_matches = len(cdm_procedures & new_treatments)
            partial_matches = 0
            for cdm_proc in cdm_procedures:
                for new_treat in new_treatments:
                    if cdm_proc in new_treat or new_treat in cdm_proc:
                        partial_matches += 1
                        break

            comparison["procedures_exact_matches"] = exact_matches
            comparison["procedures_partial_matches"] = partial_matches

        results.append(comparison)

    # Generate output file path if not provided
    if output_file is None:
        # Save in the output subdirectory
        script_dir = Path(__file__).parent
        output_dir = script_dir / "output"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "summary.txt"

    # Collect summary lines for both console and file
    summary_lines = []

    def add_line(line=""):
        summary_lines.append(line)
        print(line)

    # Print and collect summary
    add_line(f"\n{'=' * 80}")
    add_line("DATASET COMPARISON SUMMARY")
    add_line(f"{'=' * 80}\n")

    found_cases = [r for r in results if r["found"]]
    not_found_ids = [r["hadm_id"] for r in results if not r["found"]]

    add_line(f"Total cases in new dataset: {len(results)}")
    add_line(f"Found in CDMv1: {len(found_cases)}")
    add_line(f"Not found in CDMv1: {len(results) - len(found_cases)}")

    if not_found_ids:
        add_line("\nCases not found in CDMv1:")
        for hadm_id in not_found_ids:
            add_line(f"  - {hadm_id}")

    if found_cases:
        add_line("\nAverage similarities (for found cases):")
        avg_history = sum(r.get("history_similarity", 0) for r in found_cases) / len(found_cases)
        avg_exam = sum(r.get("exam_similarity", 0) for r in found_cases) / len(found_cases)
        add_line(f"  History text:     {avg_history:.1%}")
        add_line(f"  Physical exam:    {avg_exam:.1%}")

        # Collect cases with low similarity
        low_history = [r["hadm_id"] for r in found_cases if r.get("history_similarity", 0) < 0.8]
        low_exam = [r["hadm_id"] for r in found_cases if r.get("exam_similarity", 0) < 0.8]

        if low_history:
            add_line(f"\n  Cases with history similarity < 80% ({len(low_history)}):")
            for hadm_id in low_history[:10]:  # Show first 10
                sim = next(
                    r.get("history_similarity", 0) for r in found_cases if r["hadm_id"] == hadm_id
                )
                add_line(f"    - {hadm_id} ({sim:.1%})")
            if len(low_history) > 10:
                add_line(f"    ... and {len(low_history) - 10} more")

        if low_exam:
            add_line(f"\n  Cases with exam similarity < 80% ({len(low_exam)}):")
            for hadm_id in low_exam:
                sim = next(
                    r.get("exam_similarity", 0) for r in found_cases if r["hadm_id"] == hadm_id
                )
                add_line(f"    - {hadm_id} ({sim:.1%})")

        add_line("\nLab tests:")
        avg_cdm_labs = sum(r.get("cdm_lab_count", 0) for r in found_cases) / len(found_cases)
        avg_new_labs = sum(r.get("new_lab_count", 0) for r in found_cases) / len(found_cases)
        total_missing = sum(r.get("lab_missing", 0) for r in found_cases)
        total_extra = sum(r.get("lab_extra", 0) for r in found_cases)
        total_with_itemid = sum(r.get("new_labs_have_itemid", 0) for r in found_cases)
        total_itemid_overlap = sum(r.get("itemid_overlap", 0) for r in found_cases)
        total_value_matches = sum(r.get("lab_value_matches", 0) for r in found_cases)
        total_value_mismatches = sum(r.get("lab_value_mismatches", 0) for r in found_cases)

        add_line(f"  Avg CDMv1 tests per case:  {avg_cdm_labs:.1f}")
        add_line(f"  Avg new tests per case:    {avg_new_labs:.1f}")
        add_line(f"  Total missing:             {total_missing}")
        add_line(f"  Total extra:               {total_extra}")
        add_line(f"  Labs with itemid:          {total_with_itemid}")
        add_line(f"  ItemID overlap:            {total_itemid_overlap}")
        add_line(f"  Value matches:             {total_value_matches}")
        add_line(f"  Value mismatches:          {total_value_mismatches}")

        # Cases with missing labs
        cases_with_missing_labs = [r["hadm_id"] for r in found_cases if r.get("lab_missing", 0) > 0]
        if cases_with_missing_labs:
            add_line(f"\n  Cases with missing lab tests ({len(cases_with_missing_labs)}):")
            for hadm_id in cases_with_missing_labs[:10]:
                r = next(x for x in found_cases if x["hadm_id"] == hadm_id)
                missing = r.get("lab_missing", 0)
                missing_itemids = r.get("lab_missing_itemids", [])
                add_line(f"    - {hadm_id} ({missing} missing): itemids {missing_itemids}")
            if len(cases_with_missing_labs) > 10:
                add_line(f"    ... and {len(cases_with_missing_labs) - 10} more")

        # Cases with extra labs
        cases_with_extra_labs = [r["hadm_id"] for r in found_cases if r.get("lab_extra", 0) > 0]
        if cases_with_extra_labs:
            add_line(f"\n  Cases with extra lab tests ({len(cases_with_extra_labs)}):")
            for hadm_id in cases_with_extra_labs[:10]:
                r = next(x for x in found_cases if x["hadm_id"] == hadm_id)
                extra = r.get("lab_extra", 0)
                extra_itemids = r.get("lab_extra_itemids", [])
                add_line(f"    - {hadm_id} ({extra} extra): itemids {extra_itemids}")
            if len(cases_with_extra_labs) > 10:
                add_line(f"    ... and {len(cases_with_extra_labs) - 10} more")

        # Cases with value mismatches
        cases_with_value_mismatch = [
            r["hadm_id"] for r in found_cases if r.get("lab_value_mismatches", 0) > 0
        ]
        if cases_with_value_mismatch:
            add_line(f"\n  Cases with lab value mismatches ({len(cases_with_value_mismatch)}):")
            for hadm_id in cases_with_value_mismatch[:10]:
                r = next(x for x in found_cases if x["hadm_id"] == hadm_id)
                mismatches = r.get("lab_value_mismatches", 0)
                mismatch_details = r.get("lab_value_mismatch_details", [])
                add_line(f"    - {hadm_id} ({mismatches} mismatches):")
                for detail in mismatch_details[:5]:  # Show first 5 mismatches
                    add_line(
                        f"      itemid {detail['itemid']}: CDMv1='{detail['cdm_value']}' vs New='{detail['new_value']}'"
                    )
                if len(mismatch_details) > 5:
                    add_line(f"      ... and {len(mismatch_details) - 5} more")
            if len(cases_with_value_mismatch) > 10:
                add_line(f"    ... and {len(cases_with_value_mismatch) - 10} more")

        add_line("\nRadiology:")
        rad_matches = sum(1 for r in found_cases if r.get("radiology_match", False))
        total_rad_with_note_id = sum(r.get("new_radiology_have_note_id", 0) for r in found_cases)
        total_exam_overlap = sum(r.get("radiology_exam_overlap", 0) for r in found_cases)
        total_exam_missing = sum(r.get("radiology_exam_missing", 0) for r in found_cases)
        total_exam_extra = sum(r.get("radiology_exam_extra", 0) for r in found_cases)

        # Calculate average text similarity
        cases_with_text = [r for r in found_cases if "radiology_text_similarity" in r]
        if cases_with_text:
            avg_text_sim = sum(r["radiology_text_similarity"] for r in cases_with_text) / len(
                cases_with_text
            )
        else:
            avg_text_sim = 0.0

        add_line(
            f"  Exact count match:         {rad_matches}/{len(found_cases)} ({rad_matches / len(found_cases):.1%})"
        )
        add_line(f"  Reports with note_id:      {total_rad_with_note_id}")
        add_line(f"  Exam name overlap:         {total_exam_overlap}")
        add_line(f"  Exam name missing:         {total_exam_missing}")
        add_line(f"  Exam name extra:           {total_exam_extra}")
        add_line(f"  Avg text similarity:   {avg_text_sim:.1%}")

        # Cases with radiology count mismatch
        rad_count_mismatch = [
            r["hadm_id"] for r in found_cases if not r.get("radiology_match", False)
        ]
        if rad_count_mismatch:
            add_line(f"\n  Cases with radiology count mismatch ({len(rad_count_mismatch)}):")
            for hadm_id in rad_count_mismatch[:10]:
                r = next(x for x in found_cases if x["hadm_id"] == hadm_id)
                cdm_count = r.get("cdm_radiology_count", 0)
                new_count = r.get("new_radiology_count", 0)
                add_line(f"    - {hadm_id} (CDMv1: {cdm_count}, New: {new_count})")
            if len(rad_count_mismatch) > 10:
                add_line(f"    ... and {len(rad_count_mismatch) - 10} more")

        # Cases with missing radiology exams
        rad_exam_missing = [
            r["hadm_id"] for r in found_cases if r.get("radiology_exam_missing", 0) > 0
        ]
        if rad_exam_missing:
            add_line(f"\n  Cases with missing radiology exam names ({len(rad_exam_missing)}):")
            for hadm_id in rad_exam_missing[:10]:
                r = next(x for x in found_cases if x["hadm_id"] == hadm_id)
                missing = r.get("radiology_exam_missing", 0)
                missing_exams = r.get("radiology_missing_exams", [])
                add_line(f"    - {hadm_id} ({missing} missing): {missing_exams}")
            if len(rad_exam_missing) > 10:
                add_line(f"    ... and {len(rad_exam_missing) - 10} more")

        # Cases with extra radiology exams
        rad_exam_extra = [r["hadm_id"] for r in found_cases if r.get("radiology_exam_extra", 0) > 0]
        if rad_exam_extra:
            add_line(f"\n  Cases with extra radiology exam names ({len(rad_exam_extra)}):")
            for hadm_id in rad_exam_extra[:10]:
                r = next(x for x in found_cases if x["hadm_id"] == hadm_id)
                extra = r.get("radiology_exam_extra", 0)
                extra_exams = r.get("radiology_extra_exams", [])
                add_line(f"    - {hadm_id} ({extra} extra): {extra_exams}")
            if len(rad_exam_extra) > 10:
                add_line(f"    ... and {len(rad_exam_extra) - 10} more")

        # Cases with low text similarity
        low_text_sim = [
            r["hadm_id"] for r in found_cases if r.get("radiology_text_similarity", 1.0) < 0.8
        ]
        if low_text_sim:
            add_line(f"\n  Cases with text similarity < 80% ({len(low_text_sim)}):")
            for hadm_id in low_text_sim[:10]:
                sim = next(
                    r.get("radiology_text_similarity", 0)
                    for r in found_cases
                    if r["hadm_id"] == hadm_id
                )
                add_line(f"    - {hadm_id} ({sim:.1%})")
            if len(low_text_sim) > 10:
                add_line(f"    ... and {len(low_text_sim) - 10} more")

        add_line("\nMicrobiology:")
        micro_matches = sum(1 for r in found_cases if r.get("micro_match", False))
        total_micro_with_itemid = sum(r.get("new_micro_have_itemid", 0) for r in found_cases)
        total_organism_overlap = sum(r.get("micro_organism_overlap", 0) for r in found_cases)
        total_organism_missing = sum(r.get("micro_organism_missing", 0) for r in found_cases)
        total_organism_extra = sum(r.get("micro_organism_extra", 0) for r in found_cases)

        add_line(
            f"  Exact count match:         {micro_matches}/{len(found_cases)} ({micro_matches / len(found_cases):.1%})"
        )
        add_line(f"  Events with test_itemid:   {total_micro_with_itemid}")
        add_line(f"  Organism overlap:          {total_organism_overlap}")
        add_line(f"  Organism missing:          {total_organism_missing}")
        add_line(f"  Organism extra:            {total_organism_extra}")

        # Cases with micro count mismatch
        micro_count_mismatch = [
            r["hadm_id"] for r in found_cases if not r.get("micro_match", False)
        ]
        if micro_count_mismatch:
            add_line(f"\n  Cases with microbiology count mismatch ({len(micro_count_mismatch)}):")
            for hadm_id in micro_count_mismatch[:10]:
                r = next(x for x in found_cases if x["hadm_id"] == hadm_id)
                cdm_count = r.get("cdm_micro_count", 0)
                new_count = r.get("new_micro_count", 0)
                add_line(f"    - {hadm_id} (CDMv1: {cdm_count}, New: {new_count})")
            if len(micro_count_mismatch) > 10:
                add_line(f"    ... and {len(micro_count_mismatch) - 10} more")

        # Cases with missing organisms
        micro_organism_missing = [
            r["hadm_id"] for r in found_cases if r.get("micro_organism_missing", 0) > 0
        ]
        if micro_organism_missing:
            add_line(f"\n  Cases with missing organisms ({len(micro_organism_missing)}):")
            for hadm_id in micro_organism_missing[:10]:
                r = next(x for x in found_cases if x["hadm_id"] == hadm_id)
                missing = r.get("micro_organism_missing", 0)
                missing_values = r.get("micro_missing_values", [])
                add_line(f"    - {hadm_id} ({missing} missing): {missing_values}")
            if len(micro_organism_missing) > 10:
                add_line(f"    ... and {len(micro_organism_missing) - 10} more")

        # Cases with extra organisms
        micro_organism_extra = [
            r["hadm_id"] for r in found_cases if r.get("micro_organism_extra", 0) > 0
        ]
        if micro_organism_extra:
            add_line(f"\n  Cases with extra organisms ({len(micro_organism_extra)}):")
            for hadm_id in micro_organism_extra[:10]:
                r = next(x for x in found_cases if x["hadm_id"] == hadm_id)
                extra = r.get("micro_organism_extra", 0)
                extra_values = r.get("micro_extra_values", [])
                add_line(f"    - {hadm_id} ({extra} extra): {extra_values}")
            if len(micro_organism_extra) > 10:
                add_line(f"    ... and {len(micro_organism_extra) - 10} more")

        add_line("\nDiagnosis:")
        diag_matches = sum(1 for r in found_cases if r.get("diagnosis_in_discharge", False))
        avg_num_diagnoses = sum(r.get("num_diagnoses", 1) for r in found_cases) / len(found_cases)
        add_line(
            f"  Diagnosis match:           {diag_matches}/{len(found_cases)} ({diag_matches / len(found_cases):.1%})"
        )
        add_line(f"  Avg diagnoses per case:    {avg_num_diagnoses:.1f}")

        # Cases with diagnosis not found
        diag_not_found = [
            r["hadm_id"] for r in found_cases if not r.get("diagnosis_in_discharge", False)
        ]
        if diag_not_found:
            add_line(f"\n  Cases with diagnosis not found ({len(diag_not_found)}):")
            for hadm_id in diag_not_found[:10]:
                r = next(x for x in found_cases if x["hadm_id"] == hadm_id)
                diag = r.get("diagnosis")
                add_line(f"    - {hadm_id} ({diag})")
            if len(diag_not_found) > 10:
                add_line(f"    ... and {len(diag_not_found) - 10} more")

        add_line("\nDemographics:")
        has_demo = sum(1 for r in found_cases if r.get("has_demographics", False))
        has_age = sum(1 for r in found_cases if r.get("has_age", False))
        has_gender = sum(1 for r in found_cases if r.get("has_gender", False))
        add_line(
            f"  Cases with demographics:   {has_demo}/{len(found_cases)} ({has_demo / len(found_cases):.1%})"
        )
        add_line(
            f"  Cases with age:            {has_age}/{len(found_cases)} ({has_age / len(found_cases):.1%})"
        )
        add_line(
            f"  Cases with gender:         {has_gender}/{len(found_cases)} ({has_gender / len(found_cases):.1%})"
        )

        # Cases missing demographics
        missing_demo = [r["hadm_id"] for r in found_cases if not r.get("has_demographics", False)]
        if missing_demo:
            add_line(f"\n  Cases missing demographics ({len(missing_demo)}):")
            for hadm_id in missing_demo[:10]:
                add_line(f"    - {hadm_id}")
            if len(missing_demo) > 10:
                add_line(f"    ... and {len(missing_demo) - 10} more")

        add_line("\nProcedures/Treatments:")
        avg_cdm_proc = sum(r.get("cdm_procedures_count", 0) for r in found_cases) / len(found_cases)
        avg_new_treat = sum(r.get("new_treatments_count", 0) for r in found_cases) / len(
            found_cases
        )
        total_exact = sum(r.get("procedures_exact_matches", 0) for r in found_cases)
        total_partial = sum(r.get("procedures_partial_matches", 0) for r in found_cases)
        add_line(f"  Avg CDMv1 procedures:      {avg_cdm_proc:.1f}")
        add_line(f"  Avg new treatments:        {avg_new_treat:.1f}")
        add_line(f"  Total exact matches:       {total_exact}")
        add_line(f"  Total partial matches:     {total_partial}")

        # Cases with no procedure matches
        no_proc_match = [
            r["hadm_id"]
            for r in found_cases
            if r.get("procedures_partial_matches", 0) == 0 and r.get("cdm_procedures_count", 0) > 0
        ]
        if no_proc_match:
            add_line(f"\n  Cases with no procedure matches ({len(no_proc_match)}):")
            for hadm_id in no_proc_match:
                r = next(x for x in found_cases if x["hadm_id"] == hadm_id)
                cdm_count = r.get("cdm_procedures_count", 0)
                new_count = r.get("new_treatments_count", 0)
                add_line(f"    - {hadm_id} (CDMv1: {cdm_count}, New: {new_count})")

    add_line(f"\n{'=' * 80}\n")

    # Save summary to file
    with open(output_file, "w") as f:
        f.write("\n".join(summary_lines))

    add_line(f"Summary report saved to: {output_file}")

    return results


def main():
    """Command-line interface for dataset comparison"""
    parser = argparse.ArgumentParser(
        description="Compare new benchmark dataset with original CDMv1 dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic comparison (auto-generates report file)
  uv run cdm/database/analysis/dataset_comparison.py database/output/benchmark_data.json

  # Specify custom output file
  uv run cdm/database/analysis/dataset_comparison.py database/output/benchmark_data.json --output report.txt

  # Use custom CDMv1 directory
  uv run cdm/database/analysis/dataset_comparison.py database/output/benchmark_data.json --cdm-v1-dir /path/to/cdm_v1
        """,
    )

    parser.add_argument("dataset", help="Path to new benchmark dataset JSON file")
    parser.add_argument(
        "--cdm-v1-dir",
        default="/srv/student/cdm_v1",
        help="Directory containing CDMv1 dataset files (default: /srv/student/cdm_v1)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Path to save comparison report (default: auto-generated next to dataset)",
    )

    args = parser.parse_args()

    # Check if dataset file exists
    if not Path(args.dataset).exists():
        print(f"Error: Dataset file not found: {args.dataset}")
        return 1

    # Check if CDMv1 directory exists
    if not Path(args.cdm_v1_dir).exists():
        print(f"Error: CDMv1 directory not found: {args.cdm_v1_dir}")
        return 1

    # Run comparison
    try:
        compare_datasets(args.dataset, args.cdm_v1_dir, args.output)
        return 0
    except Exception as e:
        print(f"Error during comparison: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
