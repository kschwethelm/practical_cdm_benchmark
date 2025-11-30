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
    normal_test_names = ""

    for lab in case.get("lab_results", []):
        value = lab.get("value", "Unknown")
        unit = lab.get("unit", "")
        flag = lab.get("flag")
        ref_range = lab.get("ref_range_lower", ""), lab.get("ref_range_upper", "")

        # Format reference range if available
        ref_str = ""
        if ref_range[0] or ref_range[1]:
            ref_str = f" (ref: {ref_range[0]}-{ref_range[1]})"

        lab_line = f"- {lab.get('test_name')}: {value} {unit}{ref_str}\n"

        # Separate abnormal and normal
        if flag == "abnormal":
            abnormal_labs += lab_line
        else:
            # Just the test name for normal results
            normal_test_names += f"- {lab.get('test_name')}\n"

    # Combine results
    lab_results = ""
    if abnormal_labs:
        lab_results += "ABNORMAL RESULTS:\n" + abnormal_labs
    if normal_test_names:
        if include_all_labs:
            # Show full values for normal tests if include_all is True
            lab_results += "\nNORMAL TESTS (with values):\n"
            for lab in case.get("lab_results", []):
                if lab.get("flag") != "abnormal":
                    value = lab.get("value", "Unknown")
                    unit = lab.get("unit", "")
                    ref_range = lab.get("ref_range_lower", ""), lab.get("ref_range_upper", "")
                    ref_str = ""
                    if ref_range[0] or ref_range[1]:
                        ref_str = f" (ref: {ref_range[0]}-{ref_range[1]})"
                    lab_results += f"- {lab.get('test_name')}: {value} {unit}{ref_str}\n"
        else:
            # Just list test names performed for normal tests
            lab_results += "\nNORMAL TESTS PERFORMED:\n" + normal_test_names

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
        interpretation = micro.get("interpretation", "")

        micro_results += f"- {test_name} ({spec_type})\n"
        micro_results += f"  Organism: {organism}\n"
        if interpretation:
            micro_results += f"  Interpretation: {interpretation}\n"

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
