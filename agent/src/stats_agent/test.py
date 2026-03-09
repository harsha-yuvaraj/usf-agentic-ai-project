# import asyncio
# from typing import Annotated, Any, Callable, Dict, List, Optional, cast

# from langgraph.prebuilt import InjectedState
# from src.stats_agent.utils import download_file
# from dotenv import load_dotenv
# load_dotenv()
# from e2b_code_interpreter import Sandbox


# async def execute_code(code: str, state: Dict[str, Any]) -> Optional[dict[str, Any]]:
#     """Execute python code in an isolated environment.
#     """
    
#     with Sandbox.create() as sandbox:
#         context = sandbox.create_code_context(
#             cwd="/home/user",
#             language='python',
#             request_timeout=60_000
#         )
#         paths = state.get("file_paths", [])
#         for path in paths:
#             data = await download_file(path)
#             sandbox.files.write(path, data)
            
#         execution = sandbox.run_code(code)
#     return cast(dict[str, Any], {"result": execution})

# async def main():
#         # Example usage of the execute_code function
#     code = """
# import pandas as pd

# df = pd.read_excel("/home/user/test.xlsx")

# top = df.loc[df["Score"].idxmax()]

# print("Top scorer:")
# print(top)
# """
#     result = await execute_code(code, {"file_paths": ["test.xlsx"]})
#     print(result)  # Output: {'result': 'Hello, World!\n'}

# if __name__ == "__main__":
#     asyncio.run(main())