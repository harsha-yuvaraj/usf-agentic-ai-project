"""Define the configurable parameters for the agent."""

import os
from dataclasses import dataclass, field, fields
from typing import Annotated

from . import prompts



@dataclass(kw_only=True)
class Context:
    """The context for the agent."""

    orchestrator_prompt: str = field(
        default=prompts.ORCHESTRATOR_PROMPT,
        metadata={
            "description": "The system prompt to use for the orchestrator agent."
        },
    )

    analyst_prompt: str = field(
        default=prompts.ANALYST_PROMPT,
        metadata={
            "description": "The system prompt to use for the analyst worker agent."
        },
    )

    researcher_prompt: str = field(
        default=prompts.RESEARCHER_PROMPT,
        metadata={
            "description": "The system prompt to use for the researcher worker agent."
        },
    )

    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="openai/gpt-5.4-mini",
        metadata={
            "description": "The name of the language model to use for the orchestrator agent."
        },
    )

    analyst_model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="openai/gpt-5.4-mini",
        metadata={
            "description": "The name of the language model to use for the analyst worker agent."
        },
    )

    researcher_model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="openai/gpt-5.4-mini",
        metadata={
            "description": "The name of the language model to use for the researcher worker agent."
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

    max_orchestrator_steps: int = field(
        default=10,
        metadata={
            "description": "The maximum number of steps the orchestrator agent can take in a single conversation."
        },
    )

    max_worker_steps: int = field(
        default=5,
        metadata={
            "description": "The maximum number of steps a worker agent can take in a single delegation."
        },
    )

    firebase_get_file_url: str = field(
        default="http://127.0.0.1:5001/stats-agent-4a718/us-central1/getFile",
        metadata={
            "description": "URL to download files from Firebase Storage"
        }
    )

    backend_secret_key: str = field(
        default="REPLACE_ME",
        metadata={
            "description": "Secret key to authenticate with the backend services. Set via BACKEND_SECRET_KEY env var."
        }
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
