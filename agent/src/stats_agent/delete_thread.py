from langgraph_sdk import get_client
import argparse
import asyncio

async def delete_thread(thread_id: str):
    client = get_client(url="http://127.0.0.1:2024")
    # Using the graph deployed with the name "agent"
    assistant_id = "agent"
    # find thread
    try:
        thread = await client.threads.get(thread_id=thread_id)
    except Exception as e:
        print(f"Error retrieving thread with id {thread_id}: {e}")
        return
    
    runs = await client.runs.list(thread["thread_id"])
    for run in runs:
        print(run)
        run = await client.runs.delete(thread_id=thread_id, run_id=run["run_id"])


    await client.threads.delete(thread_id=thread_id)
    print(f"Deleted thread with id {thread_id} and all its runs.")

def main():
    asyncio.run(delete_thread())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("thread_id")
    args = parser.parse_args()

    print(f"Deleting thread {args.thread_id}")
    asyncio.run(delete_thread(args.thread_id))