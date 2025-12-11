import logging

from langchain.agents import create_agent
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from loguru import logger

from cdm.benchmark.data_models import AgentRunResult, BenchmarkOutputCDM, BenchmarkOutputFullInfo
from cdm.prompts.gen_prompt_cdm import create_system_prompt, create_user_prompt
from cdm.tools import AVAILABLE_TOOLS

logging.getLogger("httpx").setLevel(logging.WARNING)


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


async def run_llm_async(
    llm: ChatOpenAI, system_prompt: str, user_prompt: str
) -> BenchmarkOutputFullInfo:
    """Run the LLM with given system and user prompts.

    Args:
        llm: ChatOpenAI client
        system_prompt: System prompt string
        user_prompt: User prompt string

    Returns:
        Parsed benchmark output
    """
    llm = llm.with_structured_output(BenchmarkOutputFullInfo)

    try:
        response = await llm.ainvoke(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
    except Exception as e:
        logger.error(f"Failed to parse LLM response: {e}")
        raise

    return response


def build_agent(llm: ChatOpenAI, enabled_tools: list[str]):
    """Build a LangChain agent with tool calling capabilities.

    Args:
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

    # Get the enabled tools
    tools = [AVAILABLE_TOOLS[tool_name] for tool_name in enabled_tools]

    # Generate system prompt with Pydantic schema
    system_prompt = create_system_prompt()

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )
    logger.info(f"Built agent with tools: {enabled_tools}")
    return agent


async def run_agent_async(agent, patient_info: str) -> AgentRunResult:
    """Invoke agent with patient information and return parsed diagnosis output and full conversation history.

    Args:
        agent: LangChain agent
        patient_info: Patient's history of present illness

    Returns:
        Parsed benchmark output and full conversation history
    """
    # Generate user prompt with patient information
    user_prompt = create_user_prompt(patient_info)

    response = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ]
        }
    )

    try:
        parsed_output = BenchmarkOutputCDM.model_validate_json(response["messages"][-1].content)
    except Exception:
        parser = PydanticOutputParser(pydantic_object=BenchmarkOutputCDM)
        parsed_output = parser.parse(response["messages"][-1].content)

    messages_as_dicts = [msg.dict() for msg in response["messages"]]

    return AgentRunResult(parsed_output=parsed_output, messages=messages_as_dicts)
