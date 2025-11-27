import hydra
from loguru import logger
from omegaconf import DictConfig

from cdm.benchmark.utils import load_cases
from cdm.llms.agent import build_agent, build_llm, run_agent


@hydra.main(version_base=None, config_path="../configs/benchmark", config_name="cdm")
def main(cfg: DictConfig):
    """Run CDM benchmark with tool calling agent.

    The agent can dynamically query clinical tools to gather information and
    make a diagnosis based on the patient's history.
    """
    cases = load_cases(cfg.benchmark_data_path, cfg.num_cases)
    llm = build_llm(cfg.base_url, cfg.temperature)

    for idx, case in enumerate(cases):
        hadm_id = case["hadm_id"]
        patient_info = case["history_of_present_illness"]
        gt_diagnosis = case["ground_truth"]["primary_diagnosis"]

        logger.info(f"Processing case {idx + 1}/{len(cases)} (hadm_id: {hadm_id})")

        agent = build_agent(case, llm, cfg.enabled_tools)
        output = run_agent(agent, patient_info)

        print(f"\n=== CASE {idx + 1}/{len(cases)} (hadm_id={hadm_id}) ===")
        print(f"Ground truth: {gt_diagnosis}")
        print(f"Predicted: {output.final_diagnosis}")
        print(f"Full output: {output.model_dump_json(indent=2)}\n")

    logger.info("Benchmark complete")


if __name__ == "__main__":
    main()
