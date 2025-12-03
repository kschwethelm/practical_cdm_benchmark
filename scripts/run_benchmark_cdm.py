# Load environment variables from .env file BEFORE importing loguru
# This ensures LOGURU_LEVEL is available when logger is initialized
from dotenv import load_dotenv

load_dotenv()

# ruff: noqa: E402 - imports after load_dotenv() are intentional
import hydra
from loguru import logger
from omegaconf import DictConfig
from tqdm import tqdm

from cdm.benchmark.utils import load_cases
from cdm.llms.agent import build_agent, build_llm, run_agent
from cdm.tools import set_current_case


@hydra.main(version_base=None, config_path="../configs/benchmark", config_name="cdm")
def main(cfg: DictConfig):
    """Run CDM benchmark with tool calling agent.

    The agent can dynamically query clinical tools to gather information and
    make a diagnosis based on the patient's history.
    """
    dataset = load_cases(cfg.benchmark_data_path, cfg.num_cases)
    llm = build_llm(cfg.base_url, cfg.temperature)
    agent = build_agent(llm, cfg.enabled_tools)

    progress_bar = tqdm(dataset, desc="Processing cases")
    for case in progress_bar:
        progress_bar.set_postfix_str(f"hadm_id={case.hadm_id}")
        patient_info = case.history_of_present_illness
        gt_diagnosis = case.ground_truth.primary_diagnosis

        set_current_case(case)
        output = run_agent(agent, patient_info)

        logger.debug(f"Ground truth: {gt_diagnosis}")
        logger.debug(f"Predicted: {output.parsed_output.final_diagnosis}")
        logger.debug(f"Full output: {output.model_dump_json(indent=2)}\n")

    logger.success("Benchmark complete")


if __name__ == "__main__":
    main()
