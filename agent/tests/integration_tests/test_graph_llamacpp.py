import pytest

from stats_agent.graph import graph
from stats_agent.context import Context

pytestmark = pytest.mark.anyio


async def test_react_agent_simple_passthrough() -> None:
    res = await graph.ainvoke(
        {"messages": [("user", "Who is the founder of LangChain?")]},  # type: ignore
        context=Context(model="unsloth/Qwen3.5-397B-A17B"),
    )

    assert "harrison" in str(res["messages"][-1].content).lower()
