import json
from pathlib import Path

import hydra
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from loguru import logger
from omegaconf import DictConfig

import cdm.tools.labs as lab_tool
import cdm.tools.microbio_test as micro_tool
import cdm.tools.physical_exam as pe_tool
import cdm.tools.pmh as pmh_tool
from cdm.prompts.parser import retry_parse
from cdm.prompts.tool_agent import initial_info_template, prompt_template


def load_case(benchmark_path: Path, case_index: int) -> dict:
    """Load a specific case from the benchmark dataset."""
    logger.info(f"Loading case {case_index} from {benchmark_path}")

    with open(benchmark_path) as f:
        data = json.load(f)

    cases = data["cases"]
    if case_index >= len(cases):
        raise ValueError(f"Case index {case_index} out of range (max: {len(cases) - 1})")

    return cases[case_index]


def build_llm():
    """Build plain ChatOpenAI client."""
    return ChatOpenAI(
        model="default",
        base_url="http://localhost:8000/v1",
        api_key="EMPTY",
        temperature=0.2,
    )


def build_agent(case: dict, llm: ChatOpenAI):
    """Build a LangChain agent with tool calling capabilities."""
    tools = [
        pe_tool.create_physical_exam_tool(case),
        lab_tool.create_lab_tool(case),
        micro_tool.create_microbio_tool(case),
        pmh_tool.create_pmh_tool(case),
    ]

    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=prompt_template.format(),
    )


def gather_all_tool_info(case):
    """Gather all information using tools (for full mode)."""
    pe_tool_instance = pe_tool.create_physical_exam_tool(case)
    lab_tool_instance = lab_tool.create_lab_tool(case)
    microbio_tool_instance = micro_tool.create_microbio_tool(case)
    pmh_tool_instance = pmh_tool.create_pmh_tool(case)

    # Gather physical exam findings
    systems = [
        "general", "vitals", "abdominal", "cardiovascular", 
        "pulmonary", "neurological", "heent", "extremities", "skin"
    ]
    texts = []
    for s in systems:
        result = pe_tool_instance.invoke({"system": s})
        texts.append(f"- {s}: {result}")
    
    physical_exam_text = "\n\n".join(texts)
    lab_text = lab_tool_instance.invoke({"test_name": "all"})
    microbio_text = microbio_tool_instance.invoke({"test_name": "all"})
    pmh_text = pmh_tool_instance.invoke({"test_name": "all"})

    return physical_exam_text, lab_text, microbio_text, pmh_text


def run_tool_calling_mode(case: dict, llm: ChatOpenAI):
    """Run with tool calling: agent decides which tools to call."""
    logger.info("Running in tool_calling mode (agent with tools)")
    
    agent = build_agent(case, llm)
    
    # Initial message to the agent
    age = case.get("demographics", {}).get("age", "unknown")
    gender = case.get("demographics", {}).get("gender", "unknown")
    chief_complaint = case.get("chief_complaints", [])
    initial_prompt = initial_info_template.format(
        age=age, gender=gender, chief_complaint=chief_complaint
    )

    result = agent.invoke({
        "messages": [{"role": "user", "content": initial_prompt}]
    })

    content = result["messages"][-1].content
    parsed = retry_parse(llm, content, max_retries=2)
    
    return parsed, content


def run_full_mode(case: dict, llm: ChatOpenAI):
    """Run with full information provided upfront."""
    logger.info("Running in full mode (all data upfront)")
    
    # Gather all info
    physical_exam_text, labs_text, microbio_text, pmh_text = gather_all_tool_info(case)
    
    # Extract demographics
    demographics = case.get("demographics", {})
    age = demographics.get("age", "unknown")
    gender = demographics.get("gender", "unknown")
    
    # Extract chief complaints
    chief_complaints = case.get("chief_complaints", [])
    if isinstance(chief_complaints, list):
        chief_complaints_str = ", ".join(chief_complaints)
    else:
        chief_complaints_str = str(chief_complaints)
    
    # System prompt
    system_prompt = (
        "You are a medical assistant. You directly diagnose patients based on the provided information.\n"
        "Your goal is to correctly diagnose the patient. Based on the provided information you will provide a final diagnosis.\n\n"
        "You are given available diagnostic information at once:\n"
        "- Chief complaint\n"
        "- Past medical history\n"
        "- Microbiology results\n"
        "- Physical examination\n"
        "- Laboratory results\n\n"
        "Your task:\n"
        "1) Carefully read all information.\n"
        "2) Provide the SINGLE most likely final diagnosis.\n"
        "3) Briefly justify your reasoning.\n"
        "4) Propose an appropriate treatment plan.\n\n"
        "The diagnosis MUST be one of: appendicitis, cholecystitis, diverticulitis, pancreatitis\n"
        "Return your answer in JSON format:\n"
        "{\n"
        '  "diagnosis": "<diagnosis>",\n'
        '  "justification": "<2-4 sentences>",\n'
        '  "treatment_plan": "<2-4 sentences>"\n'
        "}\n"
    )
    
    user_input = (
        f"PATIENT DEMOGRAPHICS:\n"
        f"- Age: {age}\n"
        f"- Gender: {gender}\n\n"
        f"CHIEF COMPLAINT(S):\n"
        f"- {chief_complaints_str}\n\n"
        f"PAST MEDICAL HISTORY:\n"
        f"{pmh_text}\n\n"
        f"PHYSICAL EXAMINATION:\n"
        f"{physical_exam_text}\n\n"
        f"LABORATORY RESULTS:\n"
        f"{labs_text}\n\n"
        f"MICROBIOLOGY RESULTS:\n"
        f"{microbio_text}\n\n"
        "Using ALL of the above information, return the JSON."
    )
    
    result_msg = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ])
    
    content = result_msg.content
    
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = None
    
    return parsed, content


@hydra.main(version_base=None, config_path="../configs/benchmark", config_name="single_case")
def main(cfg: DictConfig):
    """Debug script to run a single case with either tool_calling or full mode."""
    
    # Get mode from config (default to 'tool_calling')
    mode = cfg.get("mode", "tool_calling")  # 'tool_calling' or 'full'
    
    # Load the case
    base_dir = Path(__file__).parent.parent
    benchmark_path = base_dir / cfg.benchmark_data_path
    case = load_case(benchmark_path, cfg.case_index)

    logger.info(f"Loaded case: hadm_id={case['hadm_id']}")
    print(f"Using case: hadm_id={case['hadm_id']}")
    print(f"Mode: {mode}")
    print(f"Ground truth diagnosis: {case['ground_truth']['primary_diagnosis']}\n")

    # Build LLM
    llm = build_llm()
    
    # Run appropriate mode
    if mode == "tool_calling":
        parsed, content = run_tool_calling_mode(case, llm)
    elif mode == "full":
        parsed, content = run_full_mode(case, llm)
    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'tool_calling' or 'full'")

    # Display results
    print("\n=== FINAL OUTPUT ===")
    if parsed:
        if isinstance(parsed, dict):
            print(json.dumps(parsed, indent=2))
        else:
            print(parsed.model_dump_json(indent=2))
    else:
        print("Unable to get correctly formatted output")
        print(f"Raw model output: {content}")


if __name__ == "__main__":
    main()
