import json
from pathlib import Path

import hydra
from langchain.agents import create_agent
from langchain_core.messages import BaseMessage

# Import tools
import cdm.Tools.physical_exam as pe_tool
import cdm.Tools.labs as lab_tool
import cdm.Tools.microbio_test as micro_tool
import cdm.Tools.pmh as pmh_tool


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
        '  "justification": "<2-4 sentences>",\n'
        '  "treatment_plan": "<2-4 sentences or short paragraphs>"\n'
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
    micro_tool.CURRENT_CASE = case
    pmh_tool.CURRENT_CASE = case

    # Build the agent
    agent = build_agent()

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

    # Detailed trace of all messages (tool calls are not displayed as AI messages)
    print("\n=== FULL TRACE ===")
    if isinstance(result, dict) and "messages" in result:
        for i, msg in enumerate(result["messages"], start=1):
            if isinstance(msg, BaseMessage):
                role = msg.type  # "human", "ai", "system", "tool"
                content = msg.content
            elif isinstance(msg, dict):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
            else:
                role = type(msg).__name__
                content = str(msg)

            print(f"\n--- Message {i} ({role.upper()}) ---")
            print(content)
    else:
        print(result)

    print("\n=== FINAL OUTPUT ===")
    if isinstance(result, dict) and "messages" in result and result["messages"]:
        last = result["messages"][-1]
        if isinstance(last, BaseMessage):
            print(last.content)
        elif isinstance(last, dict):
            print(last.get("content", last))
        else:
            print(last)
    else:
        print(result)


if __name__ == "__main__":
    main()
