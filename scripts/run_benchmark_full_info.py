# Load environment variables from .env file BEFORE importing loguru
# This ensures LOGURU_LEVEL is available when logger is initialized
from dotenv import load_dotenv

load_dotenv()

# ruff: noqa: E402 - imports after load_dotenv() are intentional
import hydra
from loguru import logger
from omegaconf import DictConfig
from tqdm import tqdm

from cdm.benchmark.utils import gather_all_info, load_cases
from cdm.llms.agent import build_llm, run_llm
from cdm.prompts.gen_prompt_full_info import create_system_prompt, create_user_prompt


@hydra.main(version_base=None, config_path="../configs/benchmark", config_name="full_info")
def main(cfg: DictConfig):
    """Run benchmark LLM by providing all information upfront (LLM as second reader)."""
    dataset = load_cases(cfg.benchmark_data_path, cfg.num_cases)
    llm = build_llm(cfg.base_url, cfg.temperature)

    system_prompt = create_system_prompt()

    progress_bar = tqdm(dataset, desc="Processing cases")
    for case in progress_bar:
        progress_bar.set_postfix_str(f"hadm_id={case.hadm_id}")
        gt_diagnosis = case.ground_truth.primary_diagnosis

        patient_info_dict = gather_all_info(case)
        user_prompt = create_user_prompt(patient_info_dict)

        response = run_llm(llm, system_prompt, user_prompt)

        logger.debug(f"Ground truth: {gt_diagnosis}")
        logger.debug(f"Predicted: {response.diagnosis}")
        logger.debug(f"Full output: {response.model_dump_json(indent=2)}\n")

    logger.success("Benchmark complete")


if __name__ == "__main__":
    main()
