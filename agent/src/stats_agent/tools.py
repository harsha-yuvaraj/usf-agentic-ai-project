import asyncio
import json
import logging
from typing import Annotated, Any, Callable, List, Optional, cast

from e2b_code_interpreter import Sandbox
from langchain.agents import create_agent
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolCallId, tool
from langchain_tavily import TavilySearch
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from pydantic import BaseModel, Field

from stats_agent.context import Context
from stats_agent.state import State
from stats_agent.utils import download_file, load_chat_model

logger = logging.getLogger(__name__)


class ToolNodeSchema(BaseModel):
    """Arguments for the tool node."""

    code: str = Field(...,
        description="The Python code to execute in the isolated environment.")
    clear_previous_charts: bool = Field(False,
        description="Set to True if you made a mistake in a previous execution and want to clear the chart/visual history for this task. Keep False to accumulate charts/visuals.")
    

def _run_in_sandbox(code: str, file_payloads: list[tuple[str, bytes]], sandbox_id: Optional[str] = None, clear_previous_charts: bool = False):
    images = []
    sandbox = None
    
    if sandbox_id:
        try:
            sandbox = Sandbox.connect(sandbox_id)
            sandbox.set_timeout(3600)
            logger.info(f"Reconnected to existing sandbox: {sandbox_id}")
        except Exception as e:
            logger.info(f"Failed to reconnect to sandbox {sandbox_id}: {e}")
            sandbox = None

    if not sandbox:
        sandbox = Sandbox.create(timeout=3600)
        logger.info(f"Created new sandbox: {sandbox.sandbox_id}")

    sandbox.create_code_context(
        cwd="/home/user",
        language="python",
        request_timeout=60_000,
    )

    try:
        for name, data in file_payloads:
            # Push file directly from LangGraph server to E2B Cloud Sandbox
            absolute_path = f"/home/user/{name}"
            check_result = sandbox.commands.run(f"[ -f '{absolute_path}' ] && echo 'exists' || echo 'missing'")
            if "exists" not in check_result.stdout:
                info = sandbox.files.write(absolute_path, data)
                logger.info(f"Wrote file {info.name} to sandbox: {info.path}")

        # Inject a safety wrapper to prevent matplotlib from leaking zombie plots between executions
        safe_code = "import matplotlib.pyplot as plt\nplt.close('all')\n" + code
        
        execution = sandbox.run_code(safe_code)

        if execution.error:
            logger.info("AI-generated code had an error.")
            logger.info(execution.error.name)
            logger.info(execution.error.value)
            logger.info(execution.error.traceback)

        for result in execution.results:
            if result.png:
                images.append(result.png)

        execution_result = {
            "stdout": execution.logs.stdout,
            "stderr": execution.logs.stderr,
            "chart": [result.text for result in execution.results if result.chart],
            "error": execution.error.to_json() if execution.error else None,
            "clear_previous_charts": clear_previous_charts,
        }

        return execution_result, images, sandbox.sandbox_id
    except Exception as e:
        logger.info(f"Execution failed: {e}")
        return {"error": str(e), "clear_previous_charts": False}, images, sandbox.sandbox_id if sandbox else None


@tool
async def delegate_to_analyst(
    task: str,
    config: RunnableConfig,
    state: Annotated[State, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Delegate a data analysis, coding, or statistical task to the Analyst.
    
    Use this when you need to load data, perform calculations, run statistical tests, or create charts.
    """
    sandbox_id = state.sandbox_id
    state_file_names = state.file_names
    context = cast(Context, config.get("configurable", {}).get("context"))
    if not context:
         from stats_agent.context import Context as ContextCls
         context = ContextCls()
    
    accumulated_images = []
    current_sandbox_id = [sandbox_id]
    
    @tool(description="Execute Python code in an isolated environment. The environment automatically has access to the user's uploaded files in the current working directory (/home/user/).", args_schema=ToolNodeSchema)
    async def local_execute_code(code: str, clear_previous_charts: bool = False) -> str:
        file_payloads = []
        for name in state_file_names:
            try:
                data = await download_file(f"attachments/{name}", context)
                file_payloads.append((name, data))
            except Exception as e:
                error_msg = f"System Error: Failed to download the uploaded file '{name}' from the backend storage. Please tell the user the file is inaccessible: {e}"
                logger.info(error_msg)
                return json.dumps({"error": error_msg})
                
        execution_result, images, new_sandbox_id = await asyncio.to_thread(
            _run_in_sandbox,
            code,
            file_payloads,
            current_sandbox_id[0],
            clear_previous_charts
        )
        
        current_sandbox_id[0] = new_sandbox_id
        
        if clear_previous_charts:
            accumulated_images.clear()
            
        if not execution_result.get("error"):
            accumulated_images.extend(images)
            
        return json.dumps(execution_result)

    model = load_chat_model(context, context.analyst_model)
    prompt = context.analyst_prompt.format(file_names=state_file_names)
    agent = create_agent(model=model, tools=[local_execute_code], system_prompt=prompt)
    
    try:
        res = await agent.ainvoke(
            {"messages": [("user", task)]},
            {"recursion_limit": 2 * context.max_worker_steps + 1}
        )
        final_content = res["messages"][-1].content
        if isinstance(final_content, list):
            # Parse block content if anthropic style
            final_content = " ".join([b.get("text", "") for b in final_content if isinstance(b, dict) and "text" in b])
    except GraphRecursionError:
        final_content = "Reached execution limit. The agent took too many steps and was terminated."
    except Exception as e:
        logger.exception("Analyst execution failed")
        final_content = f"An error occurred during Analyst execution: {str(e)}"
    
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=str(final_content),
                    tool_call_id=tool_call_id,
                )
            ],
            "images": accumulated_images,
            "sandbox_id": current_sandbox_id[0],
        }
    )


@tool
async def delegate_to_researcher(
    query: str,
    config: RunnableConfig,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Delegate a web search or domain research task to the Researcher.
    
    Use this when you need to find domain-specific knowledge, guidelines, or statistical methodologies from the web.
    """
    context = cast(Context, config.get("configurable", {}).get("context"))
    if not context:
         from stats_agent.context import Context as ContextCls
         context = ContextCls()

    @tool
    async def local_search(q: str) -> dict:
        """Search for general web results.

        This function performs a search using the Tavily search engine, which is designed
        to provide comprehensive, accurate, and trusted results. It's particularly useful
        for answering questions about current events.
        """
        wrapped = TavilySearch(max_results=context.max_search_results)
        return cast(dict[str, Any], await wrapped.ainvoke({"query": q}))
        
    model = load_chat_model(context, context.researcher_model)
    agent = create_agent(model=model, tools=[local_search], system_prompt=context.researcher_prompt)
    
    try:
        res = await agent.ainvoke(
            {"messages": [("user", query)]},
            {"recursion_limit": 2 * context.max_worker_steps + 1}
        )
        final_content = res["messages"][-1].content
        if isinstance(final_content, list):
            final_content = " ".join([b.get("text", "") for b in final_content if isinstance(b, dict) and "text" in b])
    except GraphRecursionError:
        final_content = "Reached execution limit. The agent took too many steps and was terminated."
    except Exception as e:
        logger.exception("Researcher execution failed")
        final_content = f"An error occurred during Researcher execution: {str(e)}"
    
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=str(final_content),
                    tool_call_id=tool_call_id,
                )
            ]
        }
    )

ORCHESTRATOR_TOOLS: List[Callable[..., Any]] = [delegate_to_analyst, delegate_to_researcher]
