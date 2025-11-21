import json
from pathlib import Path

import hydra
from langchain_openai import ChatOpenAI
from loguru import logger
from omegaconf import DictConfig

import cdm.Tools.labs as lab_tool
import cdm.Tools.microbio_test as microbio_tool

from cdm.Prompts.all_info import prompt_template
from cdm.Prompts.parser import parser 


def load_case(benchmark_path: Path, case_index: int) -> dict:
    """Load a specific case from the benchmark dataset."""

    logger.info(f"Loading case {case_index} from {benchmark_path}")

    with open(benchmark_path) as f:
        data = json.load(f)

    # Get the specific case
    cases = data["cases"]
    if case_index >= len(cases):
        raise ValueError(f"Case index {case_index} out of range (max: {len(cases) - 1})")

    return cases[case_index]


def build_llm():
    """Plain ChatOpenAI client (no tools, no agent graph)."""

    return ChatOpenAI(
        model="default",
        base_url="http://localhost:8000/v1",
        api_key="EMPTY",
        temperature=0.2,
    )


def gather_all_tool_info(case):
    """Gather all physical exam systems and lab results using the tools."""

    lab_tool.CURRENT_CASE = case
    microbio_tool.CURRENT_CASE = case

    # Gather lab results (e.g Barbiturate Screen because of token limit)
    lab_text = lab_tool.request_lab_test.invoke({"test_name": "Barbiturate Screen"})

    # Gather microbiology results
    microbio_text = microbio_tool.request_microbio_test.invoke({"test_name": "all"})

    return lab_text, microbio_text


@hydra.main(version_base=None, config_path="../configs/benchmark", config_name="demo")
def main(cfg: DictConfig):
    """Run a full-information workflow: tools first, then single LLM call."""

    # Load the case
    base_dir = Path(__file__).parent.parent
    benchmark_path = base_dir / cfg.benchmark_data_path
    case = load_case(benchmark_path, 0)

    logger.info(f"Loaded case: hadm_id={case['hadm_id']}")
    print(f"Using case: hadm_id={case['hadm_id']}")
    print(case)
    print(f"Ground truth diagnosis: {case['ground_truth']['primary_diagnosis']}\n")

    # Build LLM
    llm = build_llm()

    # Gather info from tools at once
    labs_text, microbio_text = gather_all_tool_info(case)

    # Extract demographics
    demographics = case.get("demographics", {})
    age = demographics.get("age", "unknown")
    gender = demographics.get("gender", "unknown")

    # Extract history of present illness
    history_of_present_illness = case.get("history_of_present_illness") or "Not available."

    # Extract physical exam
    physical_exam_text = case.get("physical_exam_text") or "Not available."

    # Redudant we do not have images
    imaging = case.get("radiology_reports") or "Not available."

    # Imaging is a dict/list, just dump it as JSON text for now
    if not isinstance(imaging, str):
        imaging = json.dumps(imaging, indent=2)

    prompt = prompt_template.format(
        age=age,
        gender=gender,
        history_of_present_illness=history_of_present_illness,
        physical_exam_text=physical_exam_text,
        labs_text=labs_text,
        microbio_text=microbio_text,
    )

    print("\n=== PROMPT ===\n")
    print(prompt)

    # Single call, no tool calling
    result = llm.invoke([{"role": "user", "content": prompt}])

    print("\n=== MODEL OUTPUT ===\n")
    try: 
        parsed = parser.parse(result.content) 
        print(parsed.model_dump_json(indent=2))
    except: 
        print("Unable to get correctly formatted output")
        print(f"Raw model output: {result.content}")

if __name__ == "__main__":
    main()
