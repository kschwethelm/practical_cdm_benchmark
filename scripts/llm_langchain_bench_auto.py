import json
from pathlib import Path
import yaml
import hydra
from omegaconf import DictConfig
from loguru import logger

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import BaseMessage

# Import tools
import cdm.Tools.physical_exam as pe_tool
import cdm.Tools.labs as lab_tool
import cdm.Tools.microbio_test as micro_tool
import cdm.Tools.pmh as pmh_tool

# Import evaluation metrics
import cdm.eval.acc_metrics as acc_metrics

# Import prompts & parser
from cdm.Prompts.tool_agent import prompt_template, initial_info_template
from cdm.Prompts.parser import retry_parse
from scripts.util import get_msg_content, print_trace


def load_cases(benchmark_path: Path) -> dict:
    """Load all cases from the benchmark dataset."""

    logger.info(f"Loading all cases from {benchmark_path}")

    with open(benchmark_path) as f:
        data = json.load(f)

    return data["cases"]


def build_agent():
    """Build a LangChain agent with tool calling capabilities."""
    tools = [pe_tool.request_physical_exam, lab_tool.request_lab_test, micro_tool.request_microbio_test, pmh_tool.request_past_medical_history]

    llm = ChatOpenAI(
        model="default",
        base_url="http://localhost:8000/v1",
        api_key="EMPTY",
        temperature=0.2,
    )

    # Build the agent with the specified tools and system prompt
    base_agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=prompt_template.format(),
    )

    return llm, base_agent


@hydra.main(version_base=None, config_path="../configs/benchmark", config_name="demo")
def main(cfg: DictConfig):
    """Main function to run the mock clinical workflow loop with LangChain agent."""
    # Load all cases
    base_dir = Path(__file__).parent.parent
    benchmark_path = base_dir / cfg.benchmark_data_path
    cases = load_cases(benchmark_path)

    # Build the agent
    llm, agent = build_agent()

    total = len(cases)
    correct = 0

    for idx, case in enumerate(cases):
        hadm_id = case.get("hadm_id", "unknown")
        gt_dx = case.get("ground_truth", {}).get("primary_diagnosis", "other")

        logger.info(f"Processing case {idx+1}/{100} (hadm_id: {hadm_id})")

        # Set the CURRENT_CASE for tools
        pe_tool.CURRENT_CASE = case
        lab_tool.CURRENT_CASE = case
        micro_tool.CURRENT_CASE = case
        pmh_tool.CURRENT_CASE = case

        # Initial message to the agent: patient demographics and chief complaint
        age = case.get('demographics', {}).get('age', 'unknown')
        gender = case.get('demographics', {}).get('gender', 'unknown')
        chief_complaint = case.get('chief_complaints', [])
        initial_prompt = initial_info_template.format(age=age, gender=gender, chief_complaint=chief_complaint)


        # Invoke; inside this, the agent can call tools multiple times.
        result = agent.invoke(
            {
                "messages": [
                    {"role": "user", "content": initial_prompt},
                ]
            }
        )

        # Get final message
        raw_content = get_msg_content(result)
        max_retries = 2
        parsed = retry_parse(llm, raw_content, max_retries)
        if parsed: 
            pred_dx = parsed.diagnosis
        else: 
            try:
                pred = json.loads(raw_content)
                pred_dx = pred.get("diagnosis", "other")
            except:
                pred_dx = "other"
            
            
        # Final output of the agent for this case -> detailed trace with tools 
        print_trace(result, verbose=True)
        
        # Final output of the agent for this case -> detailed trace without tools
        # print_trace(result)
         
        # Evaluate model diagnosis against ground truth
        is_correct = acc_metrics.diagnoses_match(gt_dx, pred_dx)
        if is_correct:
            correct += 1

        # Evaluate
        print(f"\n=== CASE {idx+1}/{100} (hadm_id={hadm_id}) ===")
        print(f"Ground truth: {gt_dx}")
        print(f"Model diagnosis: {pred_dx}")
        print(f"Correct: {is_correct}")

        if idx == 99:  # For quick testing
            break
        
    accuracy = correct / 100 if total > 0 else 0.0
    print("\n============================")
    print(f"Total cases: {100}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {accuracy:.3f}")
    print("============================")


if __name__ == "__main__":
    main()