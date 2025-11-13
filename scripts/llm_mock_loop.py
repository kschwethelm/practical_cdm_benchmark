import asyncio
import json
from pathlib import Path

import yaml
from loguru import logger
from omegaconf import DictConfig
from pydantic import BaseModel

from cdm.llms.data_models import Chat
from cdm.llms.vllm_config import vLLM_Config
from cdm.llms.vllm_inference import VLLMServeClient

from cdm.benchmark.models import DiagnosisOutput

SYSTEM = (
    "You are a clinical decision-making assistant.\n"
    "Respond using this schema:\n"
    "Thought: <short reasoning>\n"
    "If you need more info, also add:\n"
    "Action: physical examination | laboratory test | imaging\n"
    "Action input: <what exactly>\n\n"

    "STRICT RULES (you MUST follow these):\n\n"

    "1. You may ONLY use information that is explicitly written in the case text.\n"
    "2. If a symptom, sign, lab, or imaging result is NOT mentioned, you MUST treat it as UNKNOWN.\n"
    "3. You MUST NOT:\n"
    "- Assume that any lab, imaging, or exam result is \"normal\" or \"abnormal\" if it is not given.\n"
    "- Say that a test was \"done\", \"ordered\", \"pending\", or \"normal\" unless the input explicitly states it.\n"
    "- State that a symptom is absent (e.g. \"no fever, no vomiting, no weight loss\") "
    "unless the input explicitly says so (e.g. \"denies fever\").\n"
    "4. When information is missing, you may ONLY:\n"
    "- Say that it is UNKNOWN.\n"
    "- Propose which tests or questions you would like to order/ask NEXT.\n"
    "- You MUST NOT make up their results.\n"
    "5. If you violate these rules, your answer is considered incorrect.\n"
)


def build_hpi(case: dict) -> str:
    demo = case.get("demographics", {})
    cc = ", ".join(case.get("chief_complaints", [])) or "N/A"
    return (
        f"PATIENT DEMOGRAPHICS:\n"
        f"- Age: {demo.get('age','?')}\n"
        f"- Gender: {demo.get('gender','?')}\n\n"

        f"CHIEF COMPLAINT(S):\n- {cc}\n\n"

        f"Thought:\n"
        f"Action:\n"
        #f"Action input:\n"
    )

def build_pe(case: dict) -> str:
    pe = case.get("physical_exam", {})
    return (
        "Physical Examination (key findings):\n"
        f"VITAL SIGNS: {pe.get('vital_signs', 'Not documented')}\n"
        f"GENERAL: {pe.get('general', 'Not documented')}\n"
        f"HEENT/NECK: {pe.get('heent_neck', 'Not documented')}\n"
        f"CARDIOVASCULAR: {pe.get('cardiovascular', 'Not documented')}\n"
        f"PULMONARY: {pe.get('pulmonary', 'Not documented')}\n"
        f"ABDOMINAL: {pe.get('abdominal', 'Not documented')}\n"
        f"EXTREMITIES: {pe.get('extremities', 'Not documented')}\n"
        f"NEUROLOGICAL: {pe.get('neurological', 'Not documented')}\n"
        f"SKIN: {pe.get('skin', 'Not documented')}\n\n"

        f"Thought:\n"
        f"Action:\n"
        #f"Action input:\n"
    )

def build_final_prompt() -> str:
    return (
        f"Now provide your final output.\n\n"

        f"Thought:\n"
        f"Final diagnosis:\n"
        f"Treatment:\n"
    )

# --- Load YAML manually --- TODO: Replace with Hydra
config_path = Path(__file__).parent.parent / "configs/benchmark/demo.yaml"
with open(config_path, "r") as f:
    cfg = yaml.safe_load(f)

benchmark_data_path = cfg["benchmark_data_path"]
case_index = cfg["case_index"]

def load_case(benchmark_path: Path, case_index: int) -> dict:
    """Load a specific case from the benchmark dataset."""
    logger.info(f"Loading case {case_index} from {benchmark_path}")

    with open(benchmark_path) as f:
        data = json.load(f)

    cases = data["cases"]
    if case_index >= len(cases):
        raise ValueError(f"Case index {case_index} out of range (max: {len(cases) - 1})")

    return cases[case_index]

async def main():
    # Load the case
    base_dir = Path(__file__).parent.parent
    benchmark_path = base_dir / benchmark_data_path
    case = load_case(benchmark_path, case_index)

    logger.info(f"Loaded case: hadm_id={case['hadm_id']}")
    print(f"Using case: hadm_id={case['hadm_id']}")
    print(f"Ground truth diagnosis: {case['diagnosis']}\n")

    # Configure vLLM client
    config = vLLM_Config(temperature=0.0)
    client = VLLMServeClient(config)

    # Step 1: HPI
    hpi_prompt = build_hpi(case)
    chat = Chat.create_single_turn_chat(user_message=hpi_prompt, system_prompt=SYSTEM)
    r1 = await client.generate_content(chat)
    print("=== HPI Response ===")
    print(r1.response_text)
    print("")

    # Step 2: Physical Exam
    pe_prompt = (
        "Previous assistant reply:\n"
        f"{r1.response_text}\n\n"
        + build_pe(case)
    )
    chat = Chat.create_single_turn_chat(user_message=pe_prompt, system_prompt=SYSTEM)
    r2 = await client.generate_content(chat)
    print("=== Physical Exam Response ===")
    print(r2.response_text)
    print("")

    # Step 3: Final Diagnosis
    final_prompt = (
        "Previous assistant replies:\n"
        f"{r1.response_text}\n\n"
        f"{r2.response_text}\n\n"
        + build_final_prompt()
    )
    chat = Chat.create_single_turn_chat(user_message=final_prompt, system_prompt=SYSTEM)
    r3 = await client.generate_content(chat)
    print("=== Final Diagnosis Response ===")
    print(r3.response_text)
    print("")


if __name__ == "__main__":
    asyncio.run(main())