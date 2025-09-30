from typing import Any

from loguru import logger
from openai import AsyncOpenAI

from .data_models import Chat, LLMResponse, TokenCounts
from .vllm_config import vLLM_Config


class VLLMServeClient:
    def __init__(self, config: vLLM_Config):
        self.config = config
        self.client = AsyncOpenAI(**self.config.get_openai_client_params())

    def _format_output(self, response: Any) -> LLMResponse:
        """Convert OpenAI ChatCompletion response to LLMResponse format."""
        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            response_text=choice.message.content,
            finish_reason=choice.finish_reason,
            token_counts=TokenCounts(
                completion_token_count=usage.completion_tokens,
                prompt_token_count=usage.prompt_tokens,
            ),
        )

    async def generate_content(self, chat: Chat) -> LLMResponse:
        """Make a single chat completion request."""
        try:
            response = await self.client.chat.completions.create(
                model="default",  # model_alias can be used here
                messages=chat.to_dict(),
                **self.config.get_chat_completion_params(),
            )

            return self._format_output(response)

        except Exception as e:
            logger.error(f"Error in vLLM content generation: {type(e).__name__}: {e}")
            # Return error response
            return LLMResponse(
                response_text=None,
                finish_reason="error",
                token_counts=None,
            )
