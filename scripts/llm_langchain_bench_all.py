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
import cdm.eval.acc_metrics as acc_metrics


def load_cases(benchmark_path: Path) -> dict:
    """Load all cases from the benchmark dataset."""

    logger.info(f"Loading all cases from {benchmark_path}")

    with open(benchmark_path) as f:
        data = json.load(f)

    return data["cases"]


def build_llm():
    """Plain ChatOpenAI client (no tools, no agent graph)."""

    return ChatOpenAI(
        model="default",
        base_url="http://localhost:8000/v1",
        api_key="EMPTY",
        temperature=0.0,
    )


def gather_all_tool_info(case):
    """Gather all physical exam systems and lab results using the tools."""

    pe_tool.CURRENT_CASE = case
    lab_tool.CURRENT_CASE = case
    microbio_tool.CURRENT_CASE = case
    pmh_tool.CURRENT_CASE = case
    
    # Gather physical exam findings
    systems = ["general", "vitals", "abdominal", "cardiovascular", "pulmonary", "neurological", "heent", "extremities", "skin"]
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


@hydra.main(version_base=None, config_path="../configs/benchmark", config_name="benchmark")
def main(cfg: DictConfig):
    """Run a full-information workflow: tools first, then single LLM call."""

    # Load all cases
    base_dir = Path(__file__).parent.parent
    benchmark_path = base_dir / cfg.benchmark_data_path
    number_of_cases = cfg.number_of_cases
    cases = load_cases(benchmark_path)[:number_of_cases]


    # Build LLM
    llm = build_llm()

    # System prompt
    system_prompt = (
        "You are a medical assistant. You directly diagnose patients based on the provided information to assist a doctor in his clinical duties. "
        "Your goal is to correctly diagnose the patient. Based on the provided information you will provide a final diagnosis of the most severe pathology.\n"
        
        "You are given available diagnostic information at once, some might be not available:\n"
        "- Chief complain\n"
        "- Past medical history\n"
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
        "- Do NOT ask for more tests, you already have all available data.\n"
        "- Be concise but clinically precise.\n"
        "- The diagnosis MUST be one of the following four classes only: appendicitis, cholecystitis, diverticulitis, pancreatitis\n"
        "- Return your answer in the following JSON format:\n"
        '{\n'
        '  "diagnosis": "<appendicitis | cholecystitis | diverticulitis | pancreatitis>",\n'
        #'  "justification": "<2-4 sentences>",\n'
        #'  "treatment_plan": "<2-4 sentences or short paragraphs>"\n'
        "}\n"
    )

    total = len(cases)
    correct = 0
    unknown_count = 0
    allowed_diagnoses = {"appendicitis", "cholecystitis", "diverticulitis", "pancreatitis"}

    for idx, case in enumerate(cases):
        hadm_id = case.get("hadm_id", "unknown")
        gt_dx = case.get("diagnosis", "")

        logger.info(f"Processing case {idx+1}/{1000} (hadm_id: {hadm_id})")
            
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

        # User prompt
        user_input = (
            f"PATIENT DEMOGRAPHICS:\n"
            f"- Age: {age}\n"
            f"- Gender: {gender}\n\n"

            f"CHIEF COMPLAINT(S):\n"
            f"- {chief_complaints_str}\n\n"

            f"PAST MEDICAL HISTROY:\n"
            f"{pmh_text}\n\n"

            f"PHYSICAL EXAMINATION:\n"
            f"{physical_exam_text}\n\n"

            f"LABORATORY RESULTS:\n"
            f"{labs_text}\n\n"

            f"MICROBIOLOGY RESULTS:\n"
            f"{microbio_text}\n\n"

            "Using ALL of the above information, follow the system instructions and return the JSON."
        )

        # Single call, no tool calling
        result_msg = llm.invoke(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ]
        )

        # Parse model JSON
        try:
            pred = json.loads(result_msg.content)
            pred_dx = pred.get("diagnosis", "")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON for case {hadm_id}. Raw: {result_msg.content}")
            pred_dx = ""

        # Ground truth
        is_correct = acc_metrics.diagnoses_match(gt_dx, pred_dx)
        if is_correct:
            correct += 1

        gt_dx = acc_metrics.normalize_diagnosis(gt_dx)

        if pred_dx not in allowed_diagnoses:
            unknown_count += 1

        print(f"\n=== CASE {idx+1}/{number_of_cases} (hadm_id={hadm_id}) ===")
        print(f"Ground truth: {gt_dx}")
        print(f"Model diagnosis: {pred_dx}")
        print(f"Correct: {is_correct}")

        if idx == number_of_cases - 1:
            break
    
    accuracy = correct / number_of_cases if total > 0 else 0.0
    print("\n============================")
    print(f"Total cases: {number_of_cases}")
    print(f"Correct: {correct}")
    print(f"Unknown diagnoses: {unknown_count}")
    print(f"Accuracy: {accuracy:.3f}")
    print("============================")

if __name__ == "__main__":
    main()