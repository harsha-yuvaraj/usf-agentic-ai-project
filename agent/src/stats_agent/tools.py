"""This module provides example tools for web scraping and search functionality.

It includes a basic Tavily search function (as an example)

These tools are intended as free examples to get started. For production use,
consider implementing more robust and specialized tools tailored to your needs.
"""


import json
from typing import Any, Callable, List, Optional, cast


from langchain_tavily import TavilySearch
from langgraph.runtime import get_runtime
from e2b_code_interpreter import Sandbox
from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field
from langgraph.types import Command
from langchain.messages import ToolMessage

from stats_agent.context import Context
import asyncio

from stats_agent.utils import get_file_url

async def search(query: str, runtime: ToolRuntime) -> Optional[dict[str, Any]]:
    """Search for general web results.

    This function performs a search using the Tavily search engine, which is designed
    to provide comprehensive, accurate, and trusted results. It's particularly useful
    for answering questions about current events.
    """
    wrapped = TavilySearch(max_results=runtime.context.max_search_results)
    return cast(dict[str, Any], await wrapped.ainvoke({"query": query}))


class ToolNodeSchema(BaseModel):
    """Arguments for the tool node."""

    code: str = Field(...,
        description="The Python code to execute in the isolated environment.")
    file_names: List[str] = Field(...,
        description="A list of file names to be used in the code execution. Only provide the file names not the entire path!")
    
@tool(description="Execute Python code in an isolated environment.", args_schema=ToolNodeSchema)
async def execute_code(code: str, file_names: List[str], runtime: ToolRuntime) -> Optional[dict[str, Any]]:
    file_urls = []
    context = cast(Context, runtime.context)
    for name in file_names:
        url = await get_file_url(f"attachments/{name}", context)
        file_urls.append((name, url))

    execution_result, images = await asyncio.to_thread(
        _run_in_sandbox,
        code,
        file_urls,
    )

    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=json.dumps(execution_result),
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "images": images,
        }
    )

def _run_in_sandbox(code: str, file_urls: list[tuple[str, str]]):
    images = []
    with Sandbox.create() as sandbox:
        sandbox.create_code_context(
            cwd="/home/user",
            language="python",
            request_timeout=60_000,
        )

        for name, url in file_urls:
            # Download file inside the sandbox directly from Firebase Storage signed URL
            # Note: wget -qO avoids verbose output, and we quote the URL since it contains query params
            result = sandbox.commands.run(f"wget -qO '{name}' '{url}'")
            if result.error:
                print(f"Failed to download {name} via Signed URL: {result.stderr}")
            else:
                print(f"Downloaded file {name} to sandbox via Signed URL")

        execution = sandbox.run_code(code)

        if execution.error:
            print("AI-generated code had an error.")
            print(execution.error.name)
            print(execution.error.value)
            print(execution.error.traceback)
            print(sandbox.sandbox_id)

        for result in execution.results:
            if result.png:
                images.append(result.png)

        execution_result = {
            "stdout": execution.logs.stdout,
            "stderr": execution.logs.stderr,
            "chart": [result.text for result in execution.results if result.chart],
            "error": execution.error.to_json() if execution.error else None,
        }

    return execution_result, images



TOOLS: List[Callable[..., Any]] = [search, execute_code]
    