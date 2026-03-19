"""Utility & helper functions."""

from dataclasses import asdict

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
import httpx
from .context import Context

_LOCAL_PROVIDERS = {"unsloth", "ollama"}

def _get_local_model(context: Context, model: str, provider: str) -> BaseChatModel:
    """Get a locally hosted model"""
    if provider == "unsloth":
        return ChatOpenAI(
                model=f"unsloth/{model}",
                base_url=context.unsloth_base_url,
                api_key="sk-no-key-required",
            )
    if provider == "ollama":
        return ChatOllama(
            model=model,
            reasoning=True,
            base_url=context.ollama_base_url
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


def load_chat_model(context: Context) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name (str): String in the format 'provider/model'.
    """
    fully_specified_name = context.model

    provider, model = fully_specified_name.split("/", maxsplit=1)

    if provider in _LOCAL_PROVIDERS:
        return _get_local_model(context, model, provider)
    
    return init_chat_model(model, model_provider=provider)



async def download_file(object_path: str, context: Context) -> bytes:
    """
    Download a file from Firebase Storage.
    Input: object_path (example: attachments/file.pdf)
    Returns: file bytes
    """
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            context.firebase_get_file_url,
            params={"path": object_path},
            timeout=60,
        )

        response.raise_for_status()
        return response.content