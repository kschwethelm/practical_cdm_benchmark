import hydra
from loguru import logger
from omegaconf import DictConfig

from cdm.benchmark.utils import load_cases
from cdm.llms.agent import build_agent, build_llm, run_agent
from cdm.tools import set_current_case
import os 
from cdm.evaluators.appendicitis_evaluator import AppendicitisEvaluator
from cdm.evaluators.cholecystitis_evaluator import CholecystitisEvaluator
from cdm.evaluators.diverticulitis_evaluator import DiverticulitisEvaluator
from cdm.evaluators.pancreatitis_evaluator import PancreatitisEvaluator


@hydra.main(version_base=None, config_path="../configs/benchmark", config_name="cdm")
def main(cfg: DictConfig):
    """Run CDM benchmark with tool calling agent.

    The agent can dynamically query clinical tools to gather information and
    make a diagnosis based on the patient's history.
    """
    cases = load_cases(cfg.benchmark_data_path, cfg.num_cases)
    llm = build_llm(cfg.base_url, cfg.temperature)
    agent = build_agent(llm, cfg.enabled_tools)

    for idx, case in enumerate(cases):
        hadm_id = case["hadm_id"]
        patient_info = case["history_of_present_illness"]
        gt_diagnosis = case["ground_truth"]["primary_diagnosis"]
        gt_treatment = case["ground_truth"]["treatments"]

        logger.info(f"Processing case {idx + 1}/{len(cases)} (hadm_id: {hadm_id})")

        set_current_case(case)
        output = run_agent(agent, patient_info)
        for idx, tool in enumerate(output.messages):
            print(idx, tool)
            print("-----------------NEXT-------------------")
        print(f"\n=== CASE {idx + 1}/{len(cases)} (hadm_id={hadm_id}) ===")
        print(f"Ground truth: {gt_diagnosis}")
        print(f"Predicted: {output.prediction.final_diagnosis}")
        print(f"Full output: {output.prediction.model_dump_json(indent=2)}\n")
        
        #TODO: Replace 
        if "appendicitis" in gt_diagnosis.lower(): 
            evaluator = AppendicitisEvaluator(hadm_id=hadm_id, grounded_diagnosis=gt_diagnosis, grounded_treatment=gt_treatment)
        elif "diverticulitis" in gt_diagnosis.lower(): 
            evaluator = DiverticulitisEvaluator(hadm_id=hadm_id, grounded_diagnosis=gt_diagnosis, grounded_treatment=gt_treatment)
        elif "pancreatitis" in gt_diagnosis.lower(): 
            evaluator = PancreatitisEvaluator(hadm_id=hadm_id, grounded_diagnosis=gt_diagnosis, grounded_treatment=gt_treatment)
        elif "cholecystitis" in gt_diagnosis.lower(): 
            evaluator = CholecystitisEvaluator(hadm_id=hadm_id, grounded_diagnosis=gt_diagnosis, grounded_treatment=gt_treatment)
        evaluator.evaluate_case(output)
        evaluator.print_eval(csv_path='evaluation.csv')
    logger.info("Benchmark complete")


if __name__ == "__main__":
    main()


