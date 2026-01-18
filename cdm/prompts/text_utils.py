"""Token counting and text truncation utilities for context length control."""

import httpx
from loguru import logger
from transformers import AutoTokenizer, PreTrainedTokenizerBase


def get_model_info_from_server(base_url: str) -> tuple[str, int]:
    """Query vLLM server to get model name and context length.

    Args:
        base_url: vLLM server URL (e.g., "http://localhost:8000/v1")

    Returns:
        Tuple of (model_name, max_context_length)

    Raises:
        RuntimeError: If server query fails
    """
    # Remove /v1 suffix if present for the models endpoint
    server_url = base_url.rstrip("/")
    if server_url.endswith("/v1"):
        server_url = server_url[:-3]

    try:
        # Query vLLM server for model info
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{server_url}/v1/models")
            response.raise_for_status()
            data = response.json()

        if not data.get("data"):
            raise RuntimeError("No models found on vLLM server")

        model_data = data["data"][0]

        # Use 'root' field for actual HuggingFace model name
        model_name = model_data.get("root") or model_data.get("id")
        logger.info(f"Detected model from server: {model_name}")

        # Get max context length directly from vLLM response
        max_context = model_data.get("max_model_len", 8192)
        logger.info(f"Model max context length: {max_context}")

        return model_name, max_context

    except httpx.RequestError as e:
        raise RuntimeError(f"Failed to connect to vLLM server at {base_url}: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to get model info from server: {e}") from e


def load_tokenizer(model_name: str) -> PreTrainedTokenizerBase:
    """Load tokenizer for token counting.

    Args:
        model_name: HuggingFace model name (e.g., "meta-llama/Llama-3.3-70B-Instruct")

    Returns:
        Loaded tokenizer instance
    """
    logger.info(f"Loading tokenizer for: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    logger.info(f"Tokenizer loaded successfully (vocab size: {tokenizer.vocab_size})")
    return tokenizer


def calculate_num_tokens(tokenizer: PreTrainedTokenizerBase, text: str) -> int:
    """Calculate token count for text.

    Args:
        tokenizer: HuggingFace tokenizer instance
        text: Text to count tokens for

    Returns:
        Number of tokens in text
    """
    return len(tokenizer.encode(text))


def truncate_text(tokenizer: PreTrainedTokenizerBase, text: str, max_tokens: int) -> str:
    """Truncate text to fit within token limit.

    Args:
        tokenizer: HuggingFace tokenizer instance
        text: Text to truncate
        max_tokens: Maximum number of tokens allowed

    Returns:
        Truncated text (or original if already within limit)
    """
    tokens = tokenizer.encode(text)
    if len(tokens) <= max_tokens:
        return text

    truncated = tokens[:max_tokens]
    return tokenizer.decode(truncated, skip_special_tokens=True)
