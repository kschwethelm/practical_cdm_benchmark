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

    system_prompt = (
        "You are a clinical decision-making assistant for abdominal pain cases.\n"
        "You are connected to tools that can fetch:\n"
        "- physical examination (request_physical_exam)\n"
        "- laboratory results (request_lab_test)\n"
        "- microbiology results (request_microbio_test)\n"
        "- past medical history (request_past_medical_history)\n\n"

        "Workflow:\n"
        "1. Read the initial chief complain.\n"
        "2. Decide which information you still need.\n"
        "3. Use the tools to gather information.\n"
        "4. Iterate if needed.\n\n"

        "Important:\n"
        "- Be concise but clinically precise.\n"
        "- The diagnosis MUST be one of the following four classes only: appendicitis, cholecystitis, diverticulitis, pancreatitis.\n"
        "- Your FINAL answer MUST be in the following JSON format and you MUST output ONLY this JSON, with no extra text, no markdown, no commentary:\n"
        "{\n"
        '  "diagnosis": "<appendicitis | cholecystitis | diverticulitis | pancreatitis>",\n'
        #'  "justification": "<2-4 sentences>",\n'
        #'  "treatment_plan": "<2-4 sentences or short paragraphs>"\n'
        '  "confidence": "<low | medium | high> — <1 short sentence explaining why>"\n'
        "}\n"
    )

    # Build the agent with the specified tools and system prompt
    base_agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )

    return base_agent


@hydra.main(version_base=None, config_path="../configs/benchmark", config_name="demo")
def main(cfg: DictConfig):
    """Main function to run the mock clinical workflow loop with LangChain agent."""
    # Load all cases
    base_dir = Path(__file__).parent.parent
    benchmark_path = base_dir / cfg.benchmark_data_path
    cases = load_cases(benchmark_path)

    # Build the agent
    agent = build_agent()

    total = len(cases)
    correct = 0

    for idx, case in enumerate(cases):
        hadm_id = case.get("hadm_id", "unknown")
        gt_dx = case.get("diagnosis", "")

        logger.info(f"Processing case {idx+1}/{100} (hadm_id: {hadm_id})")

        # Set the CURRENT_CASE for tools
        pe_tool.CURRENT_CASE = case
        lab_tool.CURRENT_CASE = case
        micro_tool.CURRENT_CASE = case
        pmh_tool.CURRENT_CASE = case

        # Initial message to the agent: patient demographics and chief complaint
        user_input = (
            f"PATIENT DEMOGRAPHICS:\n"
            f"- Age: {case.get('demographics', {}).get('age', 'unknown')}\n"
            f"- Gender: {case.get('demographics', {}).get('gender', 'unknown')}\n\n"

            f"CHIEF COMPLAINT(S):\n"
            f"- {case.get('chief_complaints', [])}\n\n"
            
            "Start the clinical decision-making process."
        )

        # Invoke; inside this, the agent can call tools multiple times.
        result = agent.invoke(
            {
                "messages": [
                    {"role": "user", "content": user_input},
                ]
            }
        )

        # Get final message
        if isinstance(result, dict) and "messages" in result and result["messages"]:
            last = result["messages"][-1]
            if isinstance(last, BaseMessage):
                result_msg = last
                raw_content = last.content
            elif isinstance(last, dict):
                result_msg = last
                raw_content = last.get("content", "")
            else:
                result_msg = last
                raw_content = str(last)
        else:
            logger.error(f"No messages returned for case {hadm_id}")
            raw_content = ""
        
        # Parse model JSON
        try:
            pred = json.loads(raw_content)
            pred_dx = pred.get("diagnosis", "")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON for case {hadm_id}. Raw: {raw_content}")
            pred_dx = ""

        # Normalize GT
        gt_dx = acc_metrics.normalize_diagnosis(gt_dx)

        # Ground truth
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

        # Final output of the agent for this case -> detailed trace
        """print("\n=== FINAL OUTPUT ===")
        if isinstance(result, dict) and "messages" in result and result["messages"]:
            last = result["messages"][-1]
            if isinstance(last, BaseMessage):
                print(last.content)
            elif isinstance(last, dict):
                print(last.get("content", last))
            else:
                print(last)
        else:
            print(result)"""

    accuracy = correct / 100 if total > 0 else 0.0
    print("\n============================")
    print(f"Total cases: {100}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {accuracy:.3f}")
    print("============================")


if __name__ == "__main__":
    main()