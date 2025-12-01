import hydra
from loguru import logger
from omegaconf import DictConfig

from cdm.benchmark.utils import load_cases
from cdm.llms.agent import build_llm, run_llm
from cdm.prompts.full_info import full_info_prompt_template, system_prompt


def add_demographics(case):
    """Extract demographic information."""
    return {
        "age": case["demographics"]["age"],
        "gender": case["demographics"]["gender"],
    }


def add_clinical_history(case):
    """Extract clinical history information."""
    return {
        "history_of_present_illness": case["history_of_present_illness"],
        "physical_examination": case["physical_exam_text"],
    }


def add_laboratory_tests(case):
    """Format laboratory test results."""
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


def add_imaging_reports(case):
    """Format imaging/radiology reports."""
    imaging_results = ""
    for imaging in case.get("radiology_reports", []):
        exam_name = imaging.get("exam_name", "Unknown")
        modality = imaging.get("modality", "")
        region = imaging.get("region", "")
        findings = imaging.get("findings", "Unknown")

        imaging_results += f"- {exam_name} ({modality}, {region})\n"
        imaging_results += f"  Findings: {findings}\n\n"

    return {"imaging_reports": imaging_results}


def add_microbiology_results(case):
    """Format microbiology test results."""
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


def gather_all_info(case):
    """Gather all information by combining all data sources."""

    info = {}

    info.update(add_demographics(case))
    info.update(add_clinical_history(case))
    info.update(add_laboratory_tests(case))
    info.update(add_imaging_reports(case))
    info.update(add_microbiology_results(case))

    return info


@hydra.main(version_base=None, config_path="../configs/benchmark", config_name="full_info")
def main(cfg: DictConfig):
    """Run benchmark LLM by providing all information upfront (LLM as second reader)."""
    cases = load_cases(cfg.benchmark_data_path, cfg.num_cases)
    llm = build_llm(cfg.base_url, cfg.temperature)

    for idx, case in enumerate(cases):
        hadm_id = case["hadm_id"]
        gt_diagnosis = case["ground_truth"]["primary_diagnosis"]
        logger.info(f"Processing case {idx + 1}/{len(cases)} (hadm_id: {hadm_id})")

        patient_info_dict = gather_all_info(case)
        user_prompt = full_info_prompt_template.render(**patient_info_dict)

        response = run_llm(llm, system_prompt, user_prompt)

        final_diagnosis = response.diagnosis

        print(f"\n=== CASE {idx + 1}/{len(cases)} (hadm_id={hadm_id}) ===")
        print(f"Ground truth: {gt_diagnosis}")
        print(f"Predicted: {final_diagnosis}")
        print(f"Full output: {response.model_dump_json(indent=2)}\n")


if __name__ == "__main__":
    main()
