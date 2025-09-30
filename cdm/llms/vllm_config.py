from pydantic import BaseModel


class vLLM_Config(BaseModel):
    """Configuration class for vLLM server interactions.

    Uses OpenAI-compatible API to communicate with locally-hosted vLLM server.
    """

    # vLLM server connection parameters
    base_url: str = "http://localhost:8000/v1"
    timeout: float = 240.0
    max_retries: int = 3

    # Chat completion parameters
    temperature: float = 0.0  # Sampling temperature for generation
    max_tokens: int | None = None  # Maximum tokens to generate in completion
    chat_template_kwargs: dict = {}

    # Guided decoding parameters
    pydantic_model: type[BaseModel] | None = None

    def get_openai_client_params(self) -> dict:
        """Get parameters for OpenAI async client initialization."""
        return {
            "base_url": self.base_url,
            "api_key": "EMPTY",  # vLLM serve doesn't require real API key
            "timeout": self.timeout,
            "max_retries": self.max_retries,
        }

    def get_chat_completion_params(self) -> dict:
        """Get parameters for OpenAI chat completion requests."""
        params = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if self.pydantic_model:
            schema_to_use = self.pydantic_model

            schema_json = schema_to_use.model_json_schema()
            params["extra_body"] = {"guided_json": schema_json}

        return params
