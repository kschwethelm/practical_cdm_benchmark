import hydra
from loguru import logger
from omegaconf import DictConfig

from cdm.benchmark.data_models import BenchmarkOutputFullInfo
from cdm.benchmark.utils import load_cases
from cdm.llms.agent import build_llm, run_llm
from cdm.prompts.full_info import full_info_prompt_template, system_prompt_template


def gather_all_info(case):
    """Gather all information"""
    info = {
        "age": case["demographics"]["age"],
        "gender": case["demographics"]["gender"],
        "history_of_present_illness": case["history_of_present_illness"],
        "physical_examination": case["physical_exam_text"],
    }
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

        patient_info = full_info_prompt_template.format(**gather_all_info(case))

        response = run_llm(llm, system_prompt_template, patient_info)

        prediction = BenchmarkOutputFullInfo.model_validate_json(response)
        final_diagnosis = prediction.diagnosis

        print(f"\n=== CASE {idx + 1}/{len(cases)} (hadm_id={hadm_id}) ===")
        print(f"Ground truth: {gt_diagnosis}")
        print(f"Predicted: {final_diagnosis}")
        print(f"Full output: {prediction.model_dump_json(indent=2)}\n")


if __name__ == "__main__":
    main()
