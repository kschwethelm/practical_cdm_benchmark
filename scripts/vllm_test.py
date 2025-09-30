"""Simple vLLM question example.

1. Run: uv run vllm serve --config configs/vllm_config/qwen3_4B.yaml
2. Open another terminal and run this script.
"""

import asyncio
import json

from pydantic import BaseModel

from cdm.llms.data_models import Chat
from cdm.llms.vllm_config import vLLM_Config
from cdm.llms.vllm_inference import VLLMServeClient


class Diagnosis(BaseModel):
    possible_reasons: list[str]


async def main():
    # ----------------------
    # Standard question example
    # ----------------------
    question = "I have stomach ache. List two possible reasons."
    system_prompt = "You are a medical expert."

    # Configure vLLM client
    config = vLLM_Config(temperature=0.0)
    client = VLLMServeClient(config)

    # Create a messages
    chat = Chat.create_single_turn_chat(user_message=question, system_prompt=system_prompt)

    # Get response
    response = await client.generate_content(chat)
    print("--- Standard generation example ---")
    print(f"System prompt: {system_prompt}")
    print(f"Question: {question}")
    print(f"Response: {response.response_text}")
    print("")

    # ----------------------
    # Structured generation example
    # ----------------------
    question = "I have stomach ache. List three possible reasons."
    system_prompt = "You are a medical expert."

    # Add pydantic model to system prompt
    schema = Diagnosis.model_json_schema()
    system_prompt += (
        f"\n\nYou MUST answer in VALID JSON format according to the given schema:\n{schema}"
    )

    # Configure vLLM client with structured generation
    config = vLLM_Config(temperature=0.0, pydantic_model=Diagnosis)
    client = VLLMServeClient(config)

    # Create a messages
    chat = Chat.create_single_turn_chat(user_message=question, system_prompt=system_prompt)

    # Get response
    response = await client.generate_content(chat)
    response_text = response.response_text
    response_dict = json.loads(response_text)  # Convert JSON string to dict
    response_model = Diagnosis(**response_dict)  # Parse dict to pydantic model

    print("--- Structured generation example ---")
    print(f"# System prompt:\n{system_prompt}")
    print(f"\n# Question:\n{question}")
    print(f"\n# Response:\n{response_text}")
    print(f"\n# Parsed response:\n{response_model.model_dump_json()}")
    print("")


if __name__ == "__main__":
    asyncio.run(main())
