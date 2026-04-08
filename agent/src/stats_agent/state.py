"""Define the state structures for the agent."""

from dataclasses import dataclass, field
from operator import add
from typing import Optional, Sequence

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from typing_extensions import Annotated


def update_sandbox(left: Optional[str], right: Optional[str]) -> Optional[str]:
    """Return the right value if it is not None, else the left value."""
    return right if right is not None else left


@dataclass
class InputState:
    """Defines the input state for the agent, representing a narrower interface to the outside world.

    This class is used to define the initial state and structure of incoming data.
    """

    messages: Annotated[Sequence[AnyMessage], add_messages] = field(
        default_factory=list,
    )
    attachments: Sequence[str] = field(default_factory=list)


@dataclass
class State(InputState):
    """Represents the complete state of the agent, extending InputState with additional attributes.

    This class can be used to store any information needed throughout the agent's lifecycle.
    """

    orchestrator_steps: Annotated[int, add] = field(default=0)
    images: Annotated[Sequence[str], add] = field(default_factory=list)
    file_names: Sequence[str] = field(default_factory=list)
    sandbox_id: Annotated[Optional[str], update_sandbox] = field(default=None)


@dataclass
class OutputState:
    """Defines the output state for the agent, representing a narrower interface to the outside world.

    This class is used to define the initial state and structure of incoming data.
    """

    messages: Annotated[Sequence[AnyMessage], add_messages] = field(
        default_factory=list,
    )
    images: Annotated[Sequence[str], add] = field(default_factory=list)
