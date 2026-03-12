"""Define the configurable parameters for the agent."""

import os
from dataclasses import dataclass, field, fields
from typing import Annotated

from . import prompts



@dataclass(kw_only=True)
class Context:
    """The context for the agent."""

    system_prompt: str = field(
        default=prompts.SYSTEM_PROMPT,
        metadata={
            "description": "The system prompt to use for the agent's interactions. "
            "This prompt sets the context and behavior for the agent."
        },
    )

    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="openai/gpt-5-nano-2025-08-07",
        metadata={
            "description": "The name of the language model to use for the agent's main interactions. "
            "Should be in the form: provider/model-name."
        },
    )

    max_search_results: int = field(
        default=10,
        metadata={
            "description": "The maximum number of search results to return for each search query."
        },
    )

    ollama_base_url: str = field(
        default="http://127.0.0.1:11434",
        metadata={
            "description": "Base URL of the Ollama server"
        }
    )

    unsloth_base_url: str = field(
        default="http://127.0.0.1:8080/v1",
        metadata={
            "description": "Base URL of the llama.cpp server"
        }
    )

    max_steps: int = field(
        default=5,
        metadata={
            "description": "The maximum number of steps the agent can take in a single conversation."
        },
    )

    def __post_init__(self) -> None:
        for f in fields(self):
            if not f.init:
                continue

            env_value = os.environ.get(f.name.upper())
            if env_value is not None:
                setattr(self, f.name, self._convert(env_value, f.type))

    @staticmethod
    def _convert(value: str, typ):
        if typ is bool:
            return value.lower() in {"1", "true", "yes", "on"}
        if typ is int:
            return int(value)
        if typ is float:
            return float(value)
        return value  # string fallback
