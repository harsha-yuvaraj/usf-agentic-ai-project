"""Utility & helper functions."""

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
import httpx

_LOCAL_PROVIDERS = {"unsloth"}

def _get_local_model(model: str, provider: str) -> BaseChatModel:
    """Get a locally hosted model"""
    if provider == "unsloth":
        return ChatOpenAI(
                model=f"unsloth/{model}",
                base_url="http://127.0.0.1:8080/v1",
                api_key="sk-no-key-required",
            )
    raise ValueError(f"Unknown provider: {provider}")


def get_message_text(msg: BaseMessage) -> str:
    """Get the text content of a message."""
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        txts = [c if isinstance(c, str) else (c.get("text") or "") for c in content]
        return "".join(txts).strip()


def load_chat_model(fully_specified_name: str) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name (str): String in the format 'provider/model'.
    """

    provider, model = fully_specified_name.split("/", maxsplit=1)
    if provider in _LOCAL_PROVIDERS:
        return _get_local_model(model, provider)
    return init_chat_model(model, model_provider=provider)



async def download_file(object_path: str) -> bytes:
    """
    Download a file from Firebase Storage.
    Input: object_path (example: attachments/file.pdf)
    Returns: file bytes
    """
    
    FUNCTION_URL = "http://127.0.0.1:5001/stats-agent-4a718/us-central1/getFile"
    async with httpx.AsyncClient() as client:
        response = await client.get(
            FUNCTION_URL,
            params={"path": object_path},
            timeout=60,
        )

        response.raise_for_status()
        return response.content