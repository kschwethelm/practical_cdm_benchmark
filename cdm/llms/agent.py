import json
import logging

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from loguru import logger
from openai import AsyncOpenAI
from pydantic import ValidationError

from cdm.benchmark.data_models import AgentRunResult, BenchmarkOutputCDM, BenchmarkOutputFullInfo
from cdm.prompts.gen_prompt_cdm import create_system_prompt, create_user_prompt
from cdm.tools import AVAILABLE_TOOLS, TOOL_SPECS

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


def strip_markdown_json(content: str) -> str:
    """Remove markdown code block wrapper from JSON content."""
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]  # Remove ```json
    elif content.startswith("```"):
        content = content[3:]  # Remove ```
    if content.endswith("```"):
        content = content[:-3]  # Remove trailing ```
    return content.strip()


async def run_agent_async(agent, patient_info: str) -> AgentRunResult | None:
    """Invoke agent with patient information and return parsed diagnosis output and full conversation history.

    Args:
        agent: LangChain agent
        patient_info: Patient's history of present illness

    Returns:
        Parsed benchmark output and full conversation history, or None if parsing fails
    """
    user_prompt = create_user_prompt(patient_info)
    try:
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
    except Exception as e:
        logger.error(f"Agent invocation failed: {e}")
        return None

    last_message_content = response["messages"][-1].content
    cleaned_content = strip_markdown_json(last_message_content)
    try:
        parsed_output = BenchmarkOutputCDM.model_validate_json(cleaned_content)
    except Exception as e:
        logger.error(f"Failed to validate agent output: {e}\nUnparsed output: {cleaned_content!r}")
        return None

    messages_as_dicts = [msg.dict() for msg in response["messages"]]
    return AgentRunResult(parsed_output=parsed_output, messages=messages_as_dicts)


def build_llama_llm(base_url: str) -> AsyncOpenAI:
    """
    Llama 3.3 with tool calling doesn't work with ChatOpenAI.

    :param base_url: vLLM server URL (e.g., "http://localhost:8000/v1")
    :type base_url: str
    :return: AsynOpenAI model
    :rtype: AsyncOpenAI
    """
    return AsyncOpenAI(
        base_url=base_url,
        api_key="EMPTY",
    )


def create_llama_system_prompt(enabled_tools: list[str]) -> str:
    """
    Create system prompt for Llama model with available tools and their descriptions + output formatting rules.

    :param enabled_tools: List of available tools that the model can call
    :type enabled_tools: list[str]
    :return: System prompt
    :rtype: str
    """
    tool_lines = [
        (
            f"- {tool_name}: {spec['description']}\n"
            + (
                "\n".join(f"  - {arg}: {desc}" for arg, desc in spec["args"].items())
                if spec["args"]
                else "  (no arguments)"
            )
        )
        for tool_name, spec in TOOL_SPECS.items()
    ]

    rules_section = (
        "RULES:\n"
        "- Output ONLY valid JSON\n"
        "- NO explanations\n"
        "- NO markdown\n"
        "- Tool arguments MUST match exactly\n"
        "- If a required argument is missing, you MUST NOT call the tool\n\n"
        "Tool call format:\n\n"
        "{\n"
        '  "tool": "<tool_name>",\n'
        '  "arguments": {\n'
        '    "<arg_name>": "<value>"\n'
        "  }\n"
        "}\n\n"
        "When finished, output ONLY the final JSON that matches the schema."
    )
    tool_lines = "\n".join(tool_lines)
    return f"{create_system_prompt()}\n\nAVAILABLE TOOLS:\n{tool_lines}\n\n{rules_section}"


async def run_llama_async(
    llm: AsyncOpenAI, patient_info: str, enabled_tools: list[str]
) -> AgentRunResult:
    """
    Manual tool calling loop for llama3.3

    :param llm: AsyncOpenAI model
    :type llm: AsyncOpenAI
    :param patient_info: The medical history of the patient to evaluate.
    :type patient_info: str
    :param enabled_tools: List of all available tools the model can call
    :type enabled_tools: list[str]
    :return: Parsed benchmark output and full conversation history, or None if parsing fails
    :rtype: AgentRunResult | None
    """
    system_prompt = create_llama_system_prompt(enabled_tools)

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": create_user_prompt(patient_info)},
    ]

    while True:
        try:
            response = await llm.chat.completions.create(
                model="default",
                messages=messages,
                temperature=0.0,
            )
        except Exception as e:
            logger.error(f"Llama request failed: {e}")
            return None

        content = response.choices[0].message.content
        content = strip_markdown_json(content)

        messages.append({"role": "assistant", "content": content})

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            logger.error(f"Wrong output format: \n{content}")
            return None

        if "tool" in data:
            tool_name = data["tool"]
            arguments = data.get("arguments", {})

            if tool_name not in AVAILABLE_TOOLS:
                logger.error(f"Invalid tool requested: {tool_name}")
                return None

            try:
                tool = AVAILABLE_TOOLS[tool_name]
                result = tool(**arguments)
            except Exception as e:
                logger.error(f"Tool '{tool_name}' failed: {e}")
                return None

            messages.append({"role": "tool", "name": tool_name, "content": str(result)})
            continue

        try:
            parsed = BenchmarkOutputCDM.model_validate(data)
        except ValidationError:
            logger.error(f"Validation Error:{data}")
            return None

        return AgentRunResult(parsed_output=parsed, messages=messages)
