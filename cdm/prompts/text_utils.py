"""Token counting and text truncation utilities using vLLM server endpoints."""

import httpx
from loguru import logger


class VLLMTokenizer:
    """Tokenizer that uses vLLM server's tokenize/detokenize endpoints."""

    def __init__(self, base_url: str, model_name: str):
        """Initialize tokenizer with vLLM server URL.

        Args:
            base_url: vLLM server URL (e.g., "http://localhost:8000/v1")
            model_name: Model name served by vLLM (for API calls)
        """
        self.server_url = base_url.rstrip("/")
        if self.server_url.endswith("/v1"):
            self.server_url = self.server_url[:-3]
        self.model_name = model_name
        self.client = httpx.Client(timeout=30.0)

    def encode(self, text: str) -> list[int]:
        """Tokenize text using vLLM server.

        Args:
            text: Text to tokenize

        Returns:
            List of token IDs
        """
        response = self.client.post(
            f"{self.server_url}/tokenize",
            json={"model": self.model_name, "prompt": text},
        )
        response.raise_for_status()
        data = response.json()
        return data["tokens"]

    def count_chat_tokens(self, system_prompt: str, user_prompt: str) -> int:
        """Count tokens for a chat message with proper chat template.

        Uses vLLM's messages format to apply the model's chat template,
        giving accurate token counts including special tokens.

        Args:
            system_prompt: System message content
            user_prompt: User message content

        Returns:
            Total token count including special tokens
        """
        response = self.client.post(
            f"{self.server_url}/tokenize",
            json={
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["count"]

    def decode(self, tokens: list[int], skip_special_tokens: bool = True) -> str:
        """Detokenize token IDs using vLLM server.

        Args:
            tokens: List of token IDs
            skip_special_tokens: Ignored (vLLM handles this automatically)

        Returns:
            Decoded text
        """
        response = self.client.post(
            f"{self.server_url}/detokenize",
            json={"model": self.model_name, "tokens": tokens},
        )
        response.raise_for_status()
        data = response.json()
        return data["prompt"]

    def __del__(self):
        """Close HTTP client on cleanup."""
        if hasattr(self, "client"):
            self.client.close()


def get_model_info_from_server(base_url: str) -> tuple[str, int]:
    """Query vLLM server to get model name and context length.

    Args:
        base_url: vLLM server URL (e.g., "http://localhost:8000/v1")

    Returns:
        Tuple of (model_name, max_context_length)

    Raises:
        RuntimeError: If server query fails
    """
    server_url = base_url.rstrip("/")
    if server_url.endswith("/v1"):
        server_url = server_url[:-3]

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{server_url}/v1/models")
            response.raise_for_status()
            data = response.json()

        if not data.get("data"):
            raise RuntimeError("No models found on vLLM server")

        model_data = data["data"][0]

        # Use 'id' field for API calls (served-model-name)
        model_name = model_data.get("id")
        logger.info(f"Detected model from server: {model_name}")

        max_context = model_data.get("max_model_len", 8192)
        logger.info(f"Model max context length: {max_context}")

        return model_name, max_context

    except httpx.RequestError as e:
        raise RuntimeError(f"Failed to connect to vLLM server at {base_url}: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to get model info from server: {e}") from e


def load_tokenizer(base_url: str, model_name: str) -> VLLMTokenizer:
    """Create a tokenizer that uses vLLM server endpoints.

    Args:
        base_url: vLLM server URL (e.g., "http://localhost:8000/v1")
        model_name: Model name served by vLLM

    Returns:
        VLLMTokenizer instance
    """
    logger.info(f"Using vLLM tokenizer for: {model_name}")
    return VLLMTokenizer(base_url, model_name)


def calculate_num_tokens(tokenizer: VLLMTokenizer, text: str) -> int:
    """Calculate token count for text.

    Args:
        tokenizer: VLLMTokenizer instance
        text: Text to count tokens for

    Returns:
        Number of tokens in text
    """
    return len(tokenizer.encode(text))


def truncate_text(tokenizer: VLLMTokenizer, text: str, max_tokens: int) -> str:
    """Truncate text to fit within token limit.

    Args:
        tokenizer: VLLMTokenizer instance
        text: Text to truncate
        max_tokens: Maximum number of tokens allowed

    Returns:
        Truncated text (or original if already within limit)
    """
    tokens = tokenizer.encode(text)
    if len(tokens) <= max_tokens:
        return text

    truncated = tokens[:max_tokens]
    return tokenizer.decode(truncated)
