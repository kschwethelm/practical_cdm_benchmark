"""
Educational Demo: Clinical Decision-Making Workflow with LLM

This script demonstrates how an LLM-based clinical decision support system works:
1. LLM receives initial patient information (demographics, chief complaint)
2. LLM requests diagnostic tests (lab work, imaging)
3. LLM performs physical examination
4. LLM outputs structured diagnosis and treatment recommendations

NOTE: This is a DUMMY example for educational purposes only. It simulates LLM
responses with hardcoded strings rather than actual LLM inference.
"""

import json
from pathlib import Path

import hydra
from loguru import logger
from omegaconf import DictConfig

from cdm.benchmark.models import DiagnosisOutput


def print_separator(title: str = ""):
    """Print a visual separator for better readability."""
    if title:
        print(f"\n{'=' * 80}")
        print(f"  {title}")
        print(f"{'=' * 80}\n")
    else:
        print(f"\n{'-' * 80}\n")


def simulate_tool_call(tool_name: str, parameters: dict, show_tags: bool = True):
    """Simulate an LLM tool call with XML-like tags."""
    if show_tags:
        print("<tool_call>")
        print(f"  <tool_name>{tool_name}</tool_name>")
        print("  <parameters>")
        for key, value in parameters.items():
            print(f"    <{key}>{value}</{key}>")
        print("  </parameters>")
        print("</tool_call>\n")


def simulate_tool_result(tool_name: str, result: str, show_tags: bool = True):
    """Simulate the result returned from a tool call."""
    if show_tags:
        print("<tool_result>")
        print(f"  <tool_name>{tool_name}</tool_name>")
        print("  <result>")
        print(f"    {result}")
        print("  </result>")
        print("</tool_result>\n")


def load_case(benchmark_path: Path, case_index: int) -> dict:
    """Load a specific case from the benchmark dataset."""
    logger.info(f"Loading case {case_index} from {benchmark_path}")

    with open(benchmark_path) as f:
        data = json.load(f)

    cases = data["cases"]
    if case_index >= len(cases):
        raise ValueError(f"Case index {case_index} out of range (max: {len(cases) - 1})")

    return cases[case_index]


def format_initial_prompt(case: dict) -> str:
    """Format initial patient information for LLM."""
    demographics = case["demographics"]
    hpi = case.get("history_of_present_illness", "Not available")

    prompt = f"""You are an AI clinical decision support system. A patient has arrived with the following information:

PATIENT DEMOGRAPHICS:
- Age: {demographics["age"]} years old
- Gender: {demographics["gender"]}

HISTORY OF PRESENT ILLNESS:
{hpi}

AVAILABLE TOOLS:
- request_lab_test(test_name: str) -> Get laboratory test results
- request_physical_exam(body_system: str) -> Perform physical examination
- output_diagnosis(diagnosis: str, treatment: str) -> Provide final diagnosis and treatment

Please analyze this case step by step. What would you like to do first?"""

    return prompt


@hydra.main(version_base=None, config_path="../configs/benchmark", config_name="demo")
def main(cfg: DictConfig):
    """Main demo execution."""

    print_separator("CLINICAL DECISION-MAKING WORKFLOW DEMO")
    print("This demo simulates how an LLM navigates a clinical case using tool calls.\n")
    print("NOTE: All LLM responses are hardcoded for educational purposes.\n")

    # Load the case
    base_dir = Path(__file__).parent.parent
    benchmark_path = base_dir / cfg.benchmark_data_path
    case = load_case(benchmark_path, cfg.case_index)

    logger.info(f"Loaded case: hadm_id={case['hadm_id']}")
    print(f"Using case: hadm_id={case['hadm_id']}")
    print(f"Ground Truth Diagnosis: {case['ground_truth']['primary_diagnosis']}\n")    

    # =================================================================
    # TURN 1: Initial patient presentation
    # =================================================================

    initial_prompt = format_initial_prompt(case)
    print("SYSTEM → LLM:")
    print(initial_prompt)

    print_separator()

    # Simulated LLM response
    print("LLM → SYSTEM:")
    print("<think> The patient presents with abdominal pain. This is a common symptom")
    print("with many possible causes including pancreatitis, appendicitis, cholecystitis,")
    print("or diverticulitis. I should first order laboratory tests to check for")
    print("inflammation markers and organ function.\n")
    print("I'll start by requesting laboratory tests to assess for inflammatory markers")
    print("and check pancreatic enzymes given the abdominal pain presentation.\n</think>")

    # LLM makes tool call
    simulate_tool_call(
        "request_lab_test",
        {"test_name": "comprehensive_metabolic_panel"},
        show_tags=cfg.show_tool_calls,
    )

    # =================================================================
    # TURN 2: Lab results provided, LLM continues investigation
    # =================================================================

    print("SYSTEM → LLM:")

    # Provide simulated lab results based on actual case data
    lab_results = case.get("lab_results", [])
    if lab_results:
        first_lab = lab_results[0]
        lab_info = f"""Lab Test Result:
- Test: {first_lab.get("test_name", "N/A")}
- Value: {first_lab.get("value", "N/A")}
- Unit: {first_lab.get("unit", "N/A")}"""
    else:
        lab_info = "No lab results available for this case."

    simulate_tool_result("request_lab_test", lab_info, show_tags=cfg.show_tool_calls)

    print_separator()

    print("LLM → SYSTEM:")
    print("<think> The lab results show some abnormalities. To better localize")
    print("the source of abdominal pain, I need to perform a physical examination")
    print("focusing on the abdomen to check for specific signs of tenderness,")
    print("guarding, or other findings that could indicate the underlying pathology.\n")
    print("Based on the lab results, I need to perform a focused physical examination")
    print("of the abdomen to identify the specific location and nature of the pain.\n</think>")

    # LLM makes another tool call
    simulate_tool_call(
        "request_physical_exam", {"body_system": "abdominal"}, show_tags=cfg.show_tool_calls
    )

    # =================================================================
    # TURN 3: Physical exam results, LLM ready for diagnosis
    # =================================================================

    print("SYSTEM → LLM:")

    # Provide physical exam findings
    physical_exam_text = case.get("physical_exam_text", "")
    exam_info = f"""Physical Examination Findings:

    {physical_exam_text if physical_exam_text else "Not documented"}
"""

    simulate_tool_result("request_physical_exam", exam_info, show_tags=cfg.show_tool_calls)

    print_separator()

    print("LLM → SYSTEM:")
    print("<think> Combining the clinical presentation (abdominal pain in a")
    print(f"{case['demographics']['age']}-year-old {case['demographics']['gender']}), ")
    print("laboratory findings, and physical examination showing epigastric tenderness,")
    print("the most likely diagnosis is acute pancreatitis. Treatment should include")
    print("NPO status, IV fluids for hydration, pain management, and monitoring for")
    print("complications. I'll now provide my structured diagnostic output.\n")
    print("I have sufficient information to provide a diagnosis and treatment plan.\n</think>")

    # =================================================================
    # TURN 4: Final structured output
    # =================================================================

    print("LLM → SYSTEM:")

    # LLM outputs structured JSON using Pydantic model
    diagnosis_output = DiagnosisOutput(
        diagnosis="Acute Pancreatitis",
        treatment=[
            "NPO (nothing by mouth) initially",
            "Aggressive IV fluid resuscitation with isotonic crystalloids",
            "Pain management (typically opioid analgesics)",
            "Anti-emetics for nausea/vomiting",
            "Monitor for complications (pancreatic necrosis, pseudocyst)",
            "Address underlying cause (e.g., if gallstone pancreatitis, consider cholecystectomy)",
        ],
    )

    print("STRUCTURED OUTPUT:")
    print(diagnosis_output.model_dump_json(indent=2))

    # =================================================================
    # Summary
    # =================================================================
    print_separator("WORKFLOW SUMMARY")

    print(f"Ground Truth Diagnosis: {case['ground_truth']['primary_diagnosis']}")
    print(f"LLM Predicted Diagnosis: {diagnosis_output.diagnosis}")
    print(
        f"Match: {'✓ YES' if case['ground_truth']['primary_diagnosis'].lower() in diagnosis_output.diagnosis.lower() else '✗ NO'}"    
    )

    print("\nWorkflow Steps Completed:")
    print("  1. ✓ Received initial patient information")
    print("  2. ✓ Requested and reviewed laboratory tests")
    print("  3. ✓ Performed focused physical examination")
    print("  4. ✓ Generated structured diagnosis and treatment plan")

    print("\nKey Takeaways:")
    print("  • LLMs can iteratively gather information using tool calls")
    print("  • Clinical reasoning involves synthesizing multiple data sources")
    print("  • Structured outputs enable downstream evaluation and integration")
    print("  • Real implementations would use actual LLM inference, not hardcoded responses")

    print_separator()
    logger.success("Demo completed successfully!")


if __name__ == "__main__":
    main()
