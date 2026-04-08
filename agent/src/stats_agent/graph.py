"""Define a custom Reasoning and Action agent.

Works with a chat model with tool calling support.
"""

import logging
from datetime import UTC, datetime
from typing import Any, Dict, Literal, cast

from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from langgraph.types import Command

from stats_agent.context import Context
from stats_agent.state import InputState, OutputState, State
from stats_agent.tools import ORCHESTRATOR_TOOLS
from stats_agent.utils import load_chat_model

logger = logging.getLogger(__name__)

# Define the function that calls the model


async def setup(
    state: State
) -> Dict[str, Any]:
    """Merge user attachments."""
    file_names = list(state.file_names) + list(state.attachments)

    return {"file_names": file_names}


async def call_orchestrator(
    state: State, runtime: Runtime[Context]
) -> Command[Literal["__end__", "tools"]]:
    """Call the Orchestrator LLM.

    This function prepares the prompt, initializes the model, and processes the response.

    Args:
        state (State): The current state of the conversation.
        runtime (Runtime[Context]): Configuration and context for the model run.

    Returns:
        dict: A dictionary containing the model's response message.
    """
    # Initialize the model with tool binding. Change the model or add more tools here.
    model = load_chat_model(runtime.context).bind_tools(ORCHESTRATOR_TOOLS)

    # Format the orchestrator prompt.
    system_message = runtime.context.orchestrator_prompt.format(
        system_time=datetime.now(tz=UTC).isoformat(),
        file_names=state.file_names,
    )

    
    # Get the model's response
    response = cast( # type: ignore[redundant-cast]
        AIMessage,
        await model.ainvoke(
            [{"role": "system", "content": system_message}, *state.messages]
        ),
    )

    logger.info(response.to_json())

    # Handle the case when it's the last step and the model still wants to use a tool
    if state.orchestrator_steps >= runtime.context.max_orchestrator_steps and response.tool_calls:
        return Command(
            update = {
                "orchestrator_steps": -state.orchestrator_steps,
                "messages": [
                    AIMessage(
                        id=response.id,
                        content="I have reached the maximum number of reasoning steps. Based on the analysis completed so far, here is a summary of what I found.",
                    )
                ]
            },
            goto="__end__",
        )
    # Handle the case when model wants to use tool
    elif response.tool_calls:
        return Command(
            update = {
                "orchestrator_steps": 1,
                "messages": [
                    response
                ]
            },
            goto="tools",
        )
    # Handle case where message is response to user
    else:
        return Command(
            update = {
                "orchestrator_steps": -state.orchestrator_steps,
                "messages": [
                    response
                ]
            },
            goto="__end__",
        )
    



# Define a new graph
builder = StateGraph(State, input_schema=InputState, output_schema=OutputState, context_schema=Context)

# Build nodes
builder.add_node(setup)
builder.add_node(call_orchestrator)
builder.add_node("tools", ToolNode(ORCHESTRATOR_TOOLS))

# Build edges
builder.add_edge("__start__", "setup")
builder.add_edge("setup", "call_orchestrator")
builder.add_edge("tools", "call_orchestrator")

# Compile the builder into an executable graph
graph = builder.compile(name="Stats Agent")
