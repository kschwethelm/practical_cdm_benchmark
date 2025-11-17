import json
from pathlib import Path
import yaml
import hydra
from omegaconf import DictConfig
from loguru import logger

from langchain_openai import ChatOpenAI

import cdm.Tools.physical_exam as pe_tool
import cdm.Tools.labs as lab_tool
import cdm.Tools.microbio_test as microbio_tool
import cdm.Tools.pmh as pmh_tool

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

    pe_tool.CURRENT_CASE = case
    lab_tool.CURRENT_CASE = case
    microbio_tool.CURRENT_CASE = case
    pmh_tool.CURRENT_CASE = case

    # Gather physical exam findings
    systems = [
        "general",
        "vitals",
        "abdominal",
        "cardiovascular",
        "pulmonary",
        "neurological",
        "heent",
        "extremities",
        "skin",
    ]
    texts = []

    for s in systems:
        # pe_tool is a StructuredTool -> use invoke()
        result = pe_tool.request_physical_exam.invoke({"system": s})
        texts.append(f"- {s}: {result}")

    physical_exam_text = "\n\n".join(texts)

    # Gather lab results
    lab_text = lab_tool.request_lab_test.invoke({"test_name": "all"})

    # Gather microbiology results
    microbio_text = microbio_tool.request_microbio_test.invoke({"test_name": "all"})

    # Gather past medical history
    pmh_text = pmh_tool.request_past_medical_history.invoke({"test_name": "all"})

    return physical_exam_text, lab_text, microbio_text, pmh_text


@hydra.main(version_base=None, config_path="../configs/benchmark", config_name="demo")
def main(cfg: DictConfig):
    """Run a full-information workflow: tools first, then single LLM call."""

    # Load the case
    base_dir = Path(__file__).parent.parent
    benchmark_path = base_dir / cfg.benchmark_data_path
    case = load_case(benchmark_path, cfg.case_index)

    logger.info(f"Loaded case: hadm_id={case['hadm_id']}")
    print(f"Using case: hadm_id={case['hadm_id']}")
    print(f"Ground truth diagnosis: {case['diagnosis']}\n")

    # Build LLM
    llm = build_llm()

    # Gather info from tools at once
    physical_exam_text, labs_text, microbio_text, pmh_text = gather_all_tool_info(case)

    # Extract demographics
    demographics = case.get("demographics", {})
    age = demographics.get("age", "unknown")
    gender = demographics.get("gender", "unknown")

    # Extract chief complain
    chief_complaints = case.get("chief_complaints", [])
    if isinstance(chief_complaints, list):
        chief_complaints_str = ", ".join(chief_complaints)
    else:
        chief_complaints_str = str(chief_complaints)

    # Redudant we do not have images
    imaging = case.get("imaging") or case.get("radiology_reports") or "Not available."

    # If imaging is a dict/list, just dump it as JSON text for now
    if not isinstance(imaging, str):
        imaging = json.dumps(imaging, indent=2)

    prompt = prompt_template.format(
        age=age,
        gender=gender,
        chief_complaints=chief_complaints_str,
        pmh_text=pmh_text,
        physical_exam_text=physical_exam_text,
        labs_text=labs_text,
        microbio_text=microbio_text,
    )

    print("\n=== PROMPT ===\n")
    print(prompt)

    # Single call, no tool calling
    result_msg = llm.invoke([{"role": "user", "content": prompt}])

    print("\n=== MODEL OUTPUT ===\n")
    result = parser.parse(result_msg.content)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
