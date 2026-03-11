"""Define a custom Reasoning and Action agent.

Works with a chat model with tool calling support.
"""

from datetime import UTC, datetime
from typing import Dict, List, Literal, cast

from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from langgraph.types import Command

from stats_agent.context import Context
from stats_agent.state import InputState, OutputState, State
from stats_agent.tools import TOOLS
from stats_agent.utils import load_chat_model, download_file

# Define the function that calls the model


async def call_model(
    state: State, runtime: Runtime[Context]
) -> Command[Literal["__end__", "tools"]]:
    """Call the LLM powering our "agent".

    This function prepares the prompt, initializes the model, and processes the response.

    Args:
        state (State): The current state of the conversation.
        config (RunnableConfig): Configuration for the model run.

    Returns:
        dict: A dictionary containing the model's response message.
    """
    # Initialize the model with tool binding. Change the model or add more tools here.
    model = load_chat_model(runtime.context.model).bind_tools(TOOLS)

    # Format the system prompt. Customize this to change the agent's behavior.
    system_message = runtime.context.system_prompt.format(
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
    # Handle the case when it's the last step and the model still wants to use a tool
    if state.steps >= runtime.context.max_steps and response.tool_calls:
        return Command(
            update = {
                "steps": -state.steps,
                "messages": [
                    AIMessage(
                        id=response.id,
                        content="Sorry, I could not find an answer to your question in the specified number of steps.",
                    )
                ]
            },
            goto="__end__",
        )
    # Handle the case when model wants to use tool
    elif response.tool_calls:
        return Command(
            update = {
                "steps": 1,
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
                "steps": -state.steps,
                "messages": [
                    response
                ]
            },
            goto="__end__",
        )


# Define a new graph
builder = StateGraph(State, input_schema=InputState, output_schema=OutputState, context_schema=Context)

# Build nodes
builder.add_node(call_model)
builder.add_node("tools", ToolNode(TOOLS))

# Build edges
builder.add_edge("__start__", "call_model")
builder.add_edge("tools", "call_model")

# Compile the builder into an executable graph
graph = builder.compile(name="Stats Agent")
