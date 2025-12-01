import hydra
from loguru import logger
from omegaconf import DictConfig

from cdm.benchmark.utils import gather_all_info, load_cases
from cdm.llms.agent import build_llm, run_llm
from cdm.prompts.gen_prompt_full_info import create_system_prompt, create_user_prompt


@hydra.main(version_base=None, config_path="../configs/benchmark", config_name="full_info")
def main(cfg: DictConfig):
    """Run benchmark LLM by providing all information upfront (LLM as second reader)."""
    cases = load_cases(cfg.benchmark_data_path, cfg.num_cases)
    llm = build_llm(cfg.base_url, cfg.temperature)

    system_prompt = create_system_prompt()

    for idx, case in enumerate(cases):
        hadm_id = case["hadm_id"]
        gt_diagnosis = case["ground_truth"]["primary_diagnosis"]
        logger.info(f"Processing case {idx + 1}/{len(cases)} (hadm_id: {hadm_id})")

        patient_info_dict = gather_all_info(case)
        user_prompt = create_user_prompt(patient_info_dict)

        response = run_llm(llm, system_prompt, user_prompt)

        final_diagnosis = response.diagnosis

        print(f"\n=== CASE {idx + 1}/{len(cases)} (hadm_id={hadm_id}) ===")
        print(f"Ground truth: {gt_diagnosis}")
        print(f"Predicted: {final_diagnosis}")
        print(f"Full output: {response.model_dump_json(indent=2)}\n")


if __name__ == "__main__":
    main()
