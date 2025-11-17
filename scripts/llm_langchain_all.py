import json
from pathlib import Path

import hydra
from langchain_openai import ChatOpenAI
from loguru import logger
from omegaconf import DictConfig

import cdm.Tools.labs as lab_tool
import cdm.Tools.microbio_test as microbio_tool


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

    # System prompt
    system_prompt = (
        "You are a clinical decision-making assistant for abdominal pain cases.\n"
        "You are given ALL available diagnostic information at once:\n"
        "- History of present illness\n"
        "- microbiology results\n"
        "- Physical examination\n"
        "- Laboratory results\n"
        "- Imaging reports\n\n"
        "Your task:\n"
        "1) Carefully read all information.\n"
        "2) Provide the SINGLE most likely final diagnosis responsible for the patient's presentation.\n"
        "3) Briefly justify your reasoning.\n"
        "4) Propose an appropriate initial treatment plan.\n\n"
        "Important:\n"
        "- Do NOT ask for more tests, you already have all relevant data.\n"
        "- Be concise but clinically precise.\n"
        "- Return your answer in the following JSON format:\n"
        "{\n"
        '  "diagnosis": "<ONE word>",\n'
        '  "justification": "<2-4 sentences>",\n'
        '  "treatment_plan": "<2-4 sentences or short paragraphs>"\n'
        "}\n"
    )

    # User prompt
    user_input = (
        f"PATIENT DEMOGRAPHICS:\n"
        f"- Age: {age}\n"
        f"- Gender: {gender}\n\n"
        f"HISTORY OF PRESENT ILLNESS:\n"
        f"{history_of_present_illness}\n\n"
        f"PHYSICAL EXAMINATION:\n"
        f"{physical_exam_text}\n\n"
        f"LABORATORY RESULTS:\n"
        f"{labs_text}\n\n"
        f"MICROBIOLOGY RESULTS:\n"
        f"{microbio_text}\n\n"
        "Using ALL of the above information, follow the system instructions and return the JSON."
    )

    print("\n=== SYSTEM PROMPT ===\n")
    print(system_prompt)

    print("\n=== USER PROMPT ===\n")
    print(user_input)

    # Single call, no tool calling
    result_msg = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]
    )

    print("\n=== MODEL OUTPUT ===\n")
    print(result_msg.content)


if __name__ == "__main__":
    main()
