import json
from pathlib import Path
import yaml
import hydra
from omegaconf import DictConfig
from loguru import logger

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

import cdm.Tools.physical_exam as pe_tool
import cdm.Tools.labs as lab_tool
from cdm.Prompts.tool_agent import prompt_template


def load_case(benchmark_path: Path, case_index: int) -> dict:
    """Load a specific case from the benchmark dataset."""

    logger.info(f"Loading case {case_index} from {benchmark_path}")

    with open(benchmark_path) as f:
        data = json.load(f)

    cases = data["cases"]
    if case_index >= len(cases):
        raise ValueError(f"Case index {case_index} out of range (max: {len(cases) - 1})")

    return cases[case_index]


def build_agent():
    """Build a LangChain agent with tools."""

    tools = [pe_tool.request_physical_exam, lab_tool.request_lab_test]

    llm = ChatOpenAI(
        model="default", base_url="http://localhost:8000/v1", api_key="EMPTY", temperature=0.2
    )

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=prompt_template.format(),
    )
    return agent


@hydra.main(version_base=None, config_path="../configs/benchmark", config_name="demo")
def main(cfg: DictConfig):
    """Main function to run the mock clinical workflow loop with LangChain agent."""

    # Load the case
    base_dir = Path(__file__).parent.parent
    benchmark_path = base_dir / cfg.benchmark_data_path
    case = load_case(benchmark_path, cfg.case_index)

    logger.info(f"Loaded case: hadm_id={case['hadm_id']}")
    print(f"Using case: hadm_id={case['hadm_id']}")
    print(f"Ground truth diagnosis: {case['diagnosis']}\n")

    # Set the CURRENT_CASE for tools
    pe_tool.CURRENT_CASE = case
    lab_tool.CURRENT_CASE = case

    # Build the agent
    agent = build_agent()

    # Initial message to the agent: give it the HPI
    user_input = (
        f"PATIENT DEMOGRAPHICS:\n"
        f"- Age: {case.get('demographics', {}).get('age', 'unknown')}\n"
        f"- Gender: {case.get('demographics', {}).get('gender', 'unknown')}\n\n"
        f"CHIEF COMPLAINT(S):\n"
        f"- {case.get('chief_complaints', [])}\n\n"
        "Start the clinical decision-making process."
    )

    result = agent.invoke({"messages": [{"role": "user", "content": user_input}]})

    print("\n=== FINAL OUTPUT ===")
    print(result["messages"][-1])


if __name__ == "__main__":
    main()
