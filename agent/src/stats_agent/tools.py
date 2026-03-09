"""This module provides example tools for web scraping and search functionality.

It includes a basic Tavily search function (as an example)

These tools are intended as free examples to get started. For production use,
consider implementing more robust and specialized tools tailored to your needs.
"""


from typing import Any, Callable, List, Optional, cast


from langchain_tavily import TavilySearch
from langgraph.runtime import get_runtime
from e2b_code_interpreter import Sandbox
from langchain.tools import tool
from pydantic import BaseModel, Field

from stats_agent.context import Context

from stats_agent.utils import download_file

async def search(query: str) -> Optional[dict[str, Any]]:
    """Search for general web results.

    This function performs a search using the Tavily search engine, which is designed
    to provide comprehensive, accurate, and trusted results. It's particularly useful
    for answering questions about current events.
    """
    runtime = get_runtime(Context)
    wrapped = TavilySearch(max_results=runtime.context.max_search_results)
    return cast(dict[str, Any], await wrapped.ainvoke({"query": query}))


class ToolNodeSchema(BaseModel):
    """Arguments for the tool node."""

    code: str = Field(...,
        description="The Python code to execute in the isolated environment.")
    file_names: List[str] = Field(...,
        description="A list of file names to be used in the code execution. Only provide the file names not the entire path!")

@tool(description="Execute Python code in an isolated environment.", args_schema=ToolNodeSchema)
async def execute_code(code: str, file_names: List[str]) -> Optional[dict[str, Any]]:
    """Execute python code in an isolated environment.
    """

    execution = None
    with Sandbox.create() as sandbox:
        context = sandbox.create_code_context(
            cwd="/home/user",
            language='python',
            request_timeout=60_000
        )
        for name in file_names:
            data = await download_file(f'attachments/{name}')
            info = sandbox.files.write(name, data)
            print(f'Wrote file {info.name} to sandbox: {info.path}')
            
        execution = sandbox.run_code(code)
        if execution.error:
            print('AI-generated code had an error.')
            print(execution.error.name)
            print(execution.error.value)
            print(execution.error.traceback)
            print(sandbox.sandbox_id)

    return cast(dict[str, Any], execution)



TOOLS: List[Callable[..., Any]] = [search, execute_code]
