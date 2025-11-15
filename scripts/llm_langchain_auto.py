import json
from pathlib import Path
import yaml
import hydra
from omegaconf import DictConfig
from loguru import logger

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.messages import BaseMessage

import cdm.Tools.physical_exam as pe_tool
import cdm.Tools.labs as lab_tool


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
    """
    Build a LangChain agent with tools and memory (RunnableWithMessageHistory).
    """
    tools = [pe_tool.request_physical_exam, lab_tool.request_lab_test]

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
        "- laboratory results (request_lab_test)\n\n"
        "Workflow:\n"
        "1. Read the initial history of present illness.\n"
        "2. Decide which information you still need.\n"
        "3. Use the tools to gather physical exam and lab results.\n"
        "4. Iterate if needed.\n"
        "5. When you are confident, explain your reasoning briefly and give a final diagnosis and treatment plan.\n"
        "Always use tools instead of guessing missing data."
    )

    # Base agent graph (no explicit memory yet)
    base_agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )

    # --- Memory setup ---
    # store: session_id -> InMemoryChatMessageHistory
    store = {}

    def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
        if session_id not in store:
            store[session_id] = InMemoryChatMessageHistory()
        return store[session_id]

    # Wrap the agent with message history.
    # The agent expects {"messages": [...]} as input, so we set input_messages_key="messages".
    agent_with_memory = RunnableWithMessageHistory(
        base_agent,
        get_session_history,
        input_messages_key="messages",
        # no separate history_messages_key because we pass all messages via "messages"
    )

    return agent_with_memory


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

    # Build the agent (with memory)
    agent = build_agent()

    # Use hadm_id as a stable session id for memory
    session_id = str(case["hadm_id"])

    # Initial message to the agent: give it the HPI
    user_input = (
        f"PATIENT DEMOGRAPHICS:\n"
        f"- Age: {case.get('demographics', {}).get('age', 'unknown')}\n"
        f"- Gender: {case.get('demographics', {}).get('gender', 'unknown')}\n\n"
        f"CHIEF COMPLAINT(S):\n"
        f"- {case.get('chief_complaints', [])}\n\n"
        "Start the clinical decision-making process."
    )

    # Single invoke; inside this, the agent can call tools multiple times.
    # Memory becomes useful if you invoke it again with the same session_id.
    result = agent.invoke(
        {
            "messages": [
                {"role": "user", "content": user_input},
            ]
        },
        config={"configurable": {"session_id": session_id}},
    )

    print("\n=== FINAL OUTPUT ===")

    # create_agent returns a state dict, typically with a "messages" list.
    if isinstance(result, dict) and "messages" in result:
        messages = result["messages"]
        if messages:
            last = messages[-1]
            if isinstance(last, BaseMessage):
                print(last.content)
            elif isinstance(last, dict):
                print(last.get("content", last))
            else:
                print(last)
        else:
            print(result)
    else:
        print(result)


if __name__ == "__main__":
    main()
