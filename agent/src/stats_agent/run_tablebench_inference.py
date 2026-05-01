"""Run TableBench DP examples through the stats agent (instruct-only, no attachments).

Reads JSONL rows like ``datasets/TableBench_DP.jsonl``, sends each row's ``instruction``
as the user message, and writes TableBench inference JSONL (original keys +
``model_name`` + ``prediction``) for the upstream parse/eval scripts.

Usage::

    cd agent
    uv run tablebench-inference --limit 5

    uv run python -m stats_agent.run_tablebench_inference --limit 5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

from .context import Context
from .graph import graph

logger = logging.getLogger(__name__)

# agent/src/stats_agent/run_tablebench_inference.py -> agent/
_AGENT_ROOT = Path(__file__).resolve().parents[2]


def _project_root() -> Path:
    return _AGENT_ROOT.parent


def _default_dataset_path() -> Path:
    return _project_root() / "datasets" / "TableBench_DP.jsonl"


def _sanitize_model_for_filename(model: str) -> str:
    return re.sub(r"[^\w.\-]+", "_", model)[:120]


def _message_content_to_str(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts)
    return str(content)


async def _run_one(instruction: str, context: Context) -> str:
    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content=instruction)],
            "attachments": [],
        },
        context=context,
    )
    messages = result.get("messages") or []
    if not messages:
        return ""
    last = messages[-1]
    if isinstance(last, AIMessage):
        return _message_content_to_str(last.content).strip()
    return _message_content_to_str(getattr(last, "content", last)).strip()


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TableBench instruct-only inference via stats agent.")
    p.add_argument(
        "--input",
        type=Path,
        default=_default_dataset_path(),
        help="TableBench DP JSONL path (default: ../datasets/TableBench_DP.jsonl)",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSONL path (default: ../datasets/tablebench_inference_<model>.jsonl)",
    )
    p.add_argument("--limit", type=int, default=None, help="Max rows to run (after --start).")
    p.add_argument("--start", type=int, default=0, help="Skip first N rows.")
    p.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override orchestrator model (provider/model); default from env / Context.",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="DEBUG logging.")
    return p.parse_args()


async def _async_main() -> int:
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    load_dotenv(_AGENT_ROOT / ".env")

    if not args.input.is_file():
        logger.error("Input file not found: %s", args.input)
        return 1

    context = Context(model=args.model) if args.model else Context()
    model_name = context.model

    out_path = args.output
    if out_path is None:
        out_path = (
            _project_root()
            / "datasets"
            / f"tablebench_inference_{_sanitize_model_for_filename(model_name)}.jsonl"
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)

    processed = 0
    skipped = 0
    errors = 0

    with args.input.open(encoding="utf-8") as fin, out_path.open("w", encoding="utf-8") as fout:
        for line_no, line in enumerate(fin, start=1):
            line = line.strip()
            if not line:
                continue
            if skipped < args.start:
                skipped += 1
                continue
            if args.limit is not None and processed >= args.limit:
                break

            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                logger.error("Line %s: invalid JSON: %s", line_no, e)
                errors += 1
                continue

            instruction = row.get("instruction")
            if not isinstance(instruction, str) or not instruction.strip():
                logger.error("Line %s: missing instruction", line_no)
                errors += 1
                continue

            logger.info("Row %s id=%s", processed + 1, row.get("id", "?"))

            try:
                prediction = await _run_one(instruction, context)
            except Exception:
                logger.exception("Line %s id=%s failed", line_no, row.get("id"))
                prediction = ""
                errors += 1

            out_row = {**row, "model_name": model_name, "prediction": prediction}
            fout.write(json.dumps(out_row, ensure_ascii=False) + "\n")
            fout.flush()
            processed += 1

    logger.info(
        "Wrote %s rows to %s (errors=%s)",
        processed,
        out_path,
        errors,
    )
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_async_main()))


if __name__ == "__main__":
    main()
