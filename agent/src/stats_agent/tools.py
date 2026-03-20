"""This module provides example tools for web scraping and search functionality.

It includes a basic Tavily search function (as an example)

These tools are intended as free examples to get started. For production use,
consider implementing more robust and specialized tools tailored to your needs.
"""


import json
from typing import Any, Callable, List, Optional, cast, Annotated


from langchain_tavily import TavilySearch
from langgraph.runtime import get_runtime
from langgraph.prebuilt import InjectedState
from e2b_code_interpreter import Sandbox
from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field
from langgraph.types import Command
from langchain.messages import ToolMessage

from stats_agent.context import Context
import asyncio

from stats_agent.utils import download_file

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
    
@tool(description="Execute Python code in an isolated environment. The environment automatically has access to the user's uploaded files in the current working directory (/home/user/).", args_schema=ToolNodeSchema)
async def execute_code(code: str, runtime: ToolRuntime, state: Annotated[dict, InjectedState]) -> Command:
    sandbox_id = state.get("sandbox_id") if isinstance(state, dict) else getattr(state, "sandbox_id", None)
    
    # Automatically get the files from the state instead of relying on the LLM
    state_file_names = state.get("file_names", []) if isinstance(state, dict) else getattr(state, "file_names", [])
    
    file_payloads = []
    context = cast(Context, runtime.context)
    for name in state_file_names:
        try:
            # Download file bytes from Firebase (handles local emulator -> cloud E2B bridging)
            data = await download_file(f"attachments/{name}", context)
            file_payloads.append((name, data))
        except Exception as e:
            # HARD FAIL: If the file fails to download, stop the tool immediately.
            error_msg = f"System Error: Failed to download the uploaded file '{name}' from the backend storage. Please tell the user the file is inaccessible: {e}"
            print(error_msg)
            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            content=json.dumps({"error": error_msg}),
                            tool_call_id=runtime.tool_call_id,
                        )
                    ]
                }
            )

    execution_result, images, new_sandbox_id = await asyncio.to_thread(
        _run_in_sandbox,
        code,
        file_payloads,
        sandbox_id
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
            "sandbox_id": new_sandbox_id,
        }
    )

def _run_in_sandbox(code: str, file_payloads: list[tuple[str, bytes]], sandbox_id: Optional[str] = None):
    images = []
    sandbox = None
    
    if sandbox_id:
        try:
            sandbox = Sandbox.connect(sandbox_id)
            sandbox.set_timeout(3600)
            print(f"Reconnected to existing sandbox: {sandbox_id}")
        except Exception as e:
            print(f"Failed to reconnect to sandbox {sandbox_id}: {e}")
            sandbox = None

    if not sandbox:
        sandbox = Sandbox.create(timeout=3600)
        sandbox.create_code_context(
            cwd="/home/user",
            language="python",
            request_timeout=60_000,
        )
        print(f"Created new sandbox: {sandbox.sandbox_id}")

    try:
        for name, data in file_payloads:
            # Push file directly from LangGraph server to E2B Cloud Sandbox
            # We use absolute paths to ensure the agent finds them correctly.
            absolute_path = f"/home/user/{name}"
            check_result = sandbox.commands.run(f"[ -f '{absolute_path}' ] && echo 'exists' || echo 'missing'")
            if "exists" not in check_result.stdout:
                info = sandbox.files.write(absolute_path, data)
                print(f"Wrote file {info.name} to sandbox: {info.path}")

        # Inject a safety wrapper to prevent matplotlib from leaking zombie plots between executions
        safe_code = "import matplotlib.pyplot as plt\nplt.close('all')\n" + code
        
        execution = sandbox.run_code(safe_code)

        if execution.error:
            print("AI-generated code had an error.")
            print(execution.error.name)
            print(execution.error.value)
            print(execution.error.traceback)

        for result in execution.results:
            if result.png:
                images.append(result.png)

        execution_result = {
            "stdout": execution.logs.stdout,
            "stderr": execution.logs.stderr,
            "chart": [result.text for result in execution.results if result.chart],
            "error": execution.error.to_json() if execution.error else None,
        }

        return execution_result, images, sandbox.sandbox_id
    except Exception as e:
        print(f"Execution failed: {e}")
        return {"error": str(e)}, images, sandbox.sandbox_id if sandbox else None



TOOLS: List[Callable[..., Any]] = [search, execute_code]
    