from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from loguru import logger

from cdm.benchmark.data_models import BenchmarkOutputCDM
from cdm.prompts.cdm import system_prompt_template, user_prompt_template
from cdm.tools import AVAILABLE_TOOLS


def build_llm(base_url: str, temperature: float) -> ChatOpenAI:
    """Build plain ChatOpenAI client.

    Args:
        base_url: vLLM server URL (e.g., "http://localhost:8000/v1")
        temperature: Sampling temperature (0.0 = deterministic, higher = more random)
    """
    return ChatOpenAI(
        model="default",
        base_url=base_url,
        api_key="EMPTY",
        temperature=temperature,
    )


def run_llm(llm: ChatOpenAI, system_prompt: str, user_prompt: str) -> str:
    """Run the LLM with given system and user prompts.

    Args:
        llm: ChatOpenAI client
        system_prompt: System prompt string
        user_prompt: User prompt string

    Returns:
        Model response as a string
    """
    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    return response.content


def build_agent(case: dict, llm: ChatOpenAI, enabled_tools: list[str]):
    """Build a LangChain agent with tool calling capabilities.

    Args:
        case: Case data dictionary
        llm: ChatOpenAI client
        enabled_tools: List of tool names to enable (e.g., ["physical_exam", "lab"])

    Raises:
        ValueError: If any tool name in enabled_tools is not in AVAILABLE_TOOLS
    """
    # Validate all tool names are valid
    invalid_tools = [tool for tool in enabled_tools if tool not in AVAILABLE_TOOLS]
    if invalid_tools:
        raise ValueError(
            f"Invalid tool(s): {invalid_tools}. Available tools: {list(AVAILABLE_TOOLS.keys())}"
        )

    # Create the enabled tools
    tools = [AVAILABLE_TOOLS[tool_name](case) for tool_name in enabled_tools]

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt_template.format(),
    )
    logger.info(f"Built agent with tools: {enabled_tools}")
    return agent


def run_agent(agent, patient_info: str) -> BenchmarkOutputCDM:
    """Invoke agent with patient information and return parsed diagnosis output.

    Args:
        agent: LangChain agent
        patient_info: Patient's history of present illness

    Returns:
        Parsed benchmark output
    """
    response = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt_template.format(patient_info=patient_info),
                },
            ]
        }
    )

    # Parse model output
    return BenchmarkOutputCDM.model_validate_json(response["messages"][-1].content)
