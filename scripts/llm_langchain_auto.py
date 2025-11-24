import json
from pathlib import Path

import hydra
from langchain.agents import create_agent
from langchain_core.messages import BaseMessage
from omegaconf import DictConfig
from langchain_openai import ChatOpenAI
from loguru import logger
# Import tools
import cdm.Tools.physical_exam as pe_tool
import cdm.Tools.labs as lab_tool
import cdm.Tools.microbio_test as micro_tool
import cdm.Tools.pmh as pmh_tool
from cdm.Prompts.tool_agent import prompt_template, initial_info_template
from cdm.Prompts.parser import retry_parse
from scripts.util import get_msg_content, print_trace


def load_case(benchmark_path: Path, case_index: int) -> dict:
    """Load a specific case from the benchmark dataset."""
    logger.info(f"Loading case {case_index} from {benchmark_path}")

    with open(benchmark_path) as f:
        data = json.load(f)

    cases = data["cases"]
    if case_index >= len(cases):
        raise ValueError(f"Case index {case_index} out of range (max: {len(cases) - 1})")

    return cases[case_index]


def build_agent(case: dict):
    """Build a LangChain agent with tool calling capabilities."""
    tools = [
        pe_tool.create_physical_exam_tool(case),
        lab_tool.create_lab_tool(case),
        micro_tool.create_microbio_tool(case),
        pmh_tool.create_pmh_tool(case)
    ]

    llm = ChatOpenAI(
        model="default",
        base_url="http://localhost:8000/v1",
        api_key="EMPTY",
        temperature=0.2
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
    # Load the case
    base_dir = Path(__file__).parent.parent
    benchmark_path = base_dir / cfg.benchmark_data_path
    case = load_case(benchmark_path, cfg.case_index)

    logger.info(f"Loaded case: hadm_id={case['hadm_id']}")
    print(f"Using case: hadm_id={case['hadm_id']}")
    print(f"Ground truth diagnosis: {case['ground_truth']['primary_diagnosis']}\n")

    # Build the agent (with memory) - pass case to build_agent
    print(prompt_template.format())
    llm, agent = build_agent(case)

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

    # Detailed trace of all messages (tool calls are not displayed as AI messages)
    # print_trace(result, verbose=True)

    print("\n=== FINAL OUTPUT ===")
    content = get_msg_content(result)
    max_retries = 2
    parsed = retry_parse(llm, content, max_retries)
    if parsed: 
        print(parsed.model_dump_json(indent=2))
    else: 
        print(f"Unable to get correctly formatted output after {max_retries} retries")
        print(f"Raw model output: {content}")


if __name__ == "__main__":
    main()
