import hydra
from loguru import logger
from omegaconf import DictConfig

from cdm.benchmark.utils import load_cases
from cdm.llms.agent import build_llm, run_llm
from cdm.prompts.full_info import full_info_prompt_template, system_prompt_template


def gather_all_info(case, include_all_labs=False):
    """Gather all information

    Args:
        case: Case data dictionary
        include_all_labs: If True, include all lab results with ref ranges. If False, only abnormal results with ref ranges and normal results test names.
    """

    # Format lab results
    abnormal_labs = ""
    normal_labs_with_values = ""
    normal_test_names = ""

    for lab in case.get("lab_results", []):
        value = lab.get("value", "Unknown")
        ref_range_lower = lab.get("ref_range_lower")
        ref_range_upper = lab.get("ref_range_upper")

        # Determine if abnormal by comparing value to reference ranges
        is_abnormal = False
        try:
            # Handle values like "12 mEq/L" -> take first token
            val_str = str(value).replace(",", "").split()[0]
            val_float = float(val_str)

            if ref_range_lower is not None and val_float < ref_range_lower:
                is_abnormal = True
            elif ref_range_upper is not None and val_float > ref_range_upper:
                is_abnormal = True
        except (ValueError, TypeError, IndexError):
            # If can't convert to float, skip comparison
            pass

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

        if is_abnormal:
            abnormal_labs += lab_line
        else:
            normal_labs_with_values += lab_line
            normal_test_names += f"- {lab.get('test_name')}\n"

    # Combine results
    lab_results = ""
    if abnormal_labs:
        lab_results += "1. ABNORMAL RESULTS:\n" + abnormal_labs

    if include_all_labs:
        if normal_labs_with_values:
            lab_results += "\n2. NORMAL RESULTS:\n" + normal_labs_with_values
    else:
        if normal_test_names:
            lab_results += "\n2. NORMAL TESTS PERFORMED:\n" + normal_test_names

    # Format imaging reports
    imaging_results = ""
    for imaging in case.get("radiology_reports", []):
        exam_name = imaging.get("exam_name", "Unknown")
        modality = imaging.get("modality", "")
        region = imaging.get("region", "")
        findings = imaging.get("findings", "Unknown")

        imaging_results += f"- {exam_name} ({modality}, {region})\n"
        imaging_results += f"  Findings: {findings}\n\n"

    # Format microbiology results
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

    info = {
        "age": case["demographics"]["age"],
        "gender": case["demographics"]["gender"],
        "history_of_present_illness": case["history_of_present_illness"],
        "physical_examination": case["physical_exam_text"],
        "laboratory_results": lab_results,
        "imaging_reports": imaging_results,
        "microbiology_results": micro_results,
    }
    return info


@hydra.main(version_base=None, config_path="../configs/benchmark", config_name="full_info")
def main(cfg: DictConfig):
    """Run benchmark LLM by providing all information upfront (LLM as second reader)."""
    cases = load_cases(cfg.benchmark_data_path, cfg.num_cases)
    llm = build_llm(cfg.base_url, cfg.temperature)

    # Get lab results config (default to abnormal-only if not specified)
    include_all_labs = cfg.get("lab_results", {}).get("include_all", False)

    for idx, case in enumerate(cases):
        hadm_id = case["hadm_id"]
        gt_diagnosis = case["ground_truth"]["primary_diagnosis"]
        logger.info(f"Processing case {idx + 1}/{len(cases)} (hadm_id: {hadm_id})")

        patient_info = full_info_prompt_template.format(
            **gather_all_info(case, include_all_labs=include_all_labs)
        )

        response = run_llm(llm, system_prompt_template, patient_info)

        final_diagnosis = response.diagnosis

        print(f"\n=== CASE {idx + 1}/{len(cases)} (hadm_id={hadm_id}) ===")
        print(f"Ground truth: {gt_diagnosis}")
        print(f"Predicted: {final_diagnosis}")
        print(f"Full output: {response.model_dump_json(indent=2)}\n")


if __name__ == "__main__":
    main()
