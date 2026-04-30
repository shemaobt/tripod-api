"""Parse a Claude Code execution log and emit usage / cost stats.

Used by the Claude PR review workflows to:
  1. Render a markdown table to ``$GITHUB_STEP_SUMMARY``.
  2. Write a compact JSON file uploaded as a workflow artifact, which the
     weekly cost-report workflow aggregates and posts to Discord.

The execution-file location is read from the env var ``CLAUDE_EXECUTION_FILE``
(passed in from ``steps.<id>.outputs.execution_file``). If the path is missing
or unreadable, this script writes an empty stats JSON and exits cleanly so the
job is not failed by the bookkeeping step.

Pricing constants are public Anthropic API list prices used purely as a
stable cost-equivalent for OAuth/Pro/Max usage (where actual billing is
quota-based, not per-token).
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

# USD per 1M tokens (public API list pricing — used as a stable equivalent
# regardless of OAuth/Pro/Max billing).
PRICING: dict[str, dict[str, float]] = {
    "opus": {
        "input": 15.0,
        "output": 75.0,
        "cache_read": 1.50,
        "cache_write": 18.75,
    },
    "sonnet": {
        "input": 3.0,
        "output": 15.0,
        "cache_read": 0.30,
        "cache_write": 3.75,
    },
    "haiku": {
        "input": 1.0,
        "output": 5.0,
        "cache_read": 0.10,
        "cache_write": 1.25,
    },
}

CANDIDATE_FILES: tuple[str, ...] = (
    os.environ.get("CLAUDE_EXECUTION_FILE", ""),
    f"{os.environ.get('RUNNER_TEMP', '/tmp')}/claude-execution-output.json",
    "/tmp/claude-execution-output.json",
)


def find_execution_file() -> Path | None:
    for candidate in CANDIDATE_FILES:
        if not candidate:
            continue
        path = Path(candidate)
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


def iter_events(path: Path) -> Iterable[Any]:
    """Yield each event from the execution log (handles JSON or JSONL)."""
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return
    if text.startswith("["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = []
        if isinstance(data, list):
            yield from data
        return
    # JSONL or single object
    parsed_any = False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
            parsed_any = True
        except json.JSONDecodeError:
            continue
    if parsed_any:
        return
    try:
        yield json.loads(text)
    except json.JSONDecodeError:
        return


def walk(obj: Any) -> Iterable[dict[str, Any]]:
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk(item)


def collect_stats(path: Path) -> dict[str, Any]:
    input_tokens = output_tokens = cache_read = cache_create = 0
    model: str | None = None
    turns = 0
    duration_ms = 0
    for event in iter_events(path):
        if isinstance(event, dict):
            event_type = event.get("type")
            if event_type == "assistant":
                turns += 1
            if isinstance(event.get("duration_ms"), (int, float)):
                duration_ms = max(duration_ms, int(event["duration_ms"]))
        for node in walk(event):
            if not isinstance(node, dict):
                continue
            if "input_tokens" in node and isinstance(node["input_tokens"], (int, float)):
                input_tokens += int(node["input_tokens"])
            if "output_tokens" in node and isinstance(node["output_tokens"], (int, float)):
                output_tokens += int(node["output_tokens"])
            if "cache_read_input_tokens" in node and isinstance(
                node["cache_read_input_tokens"], (int, float)
            ):
                cache_read += int(node["cache_read_input_tokens"])
            if "cache_creation_input_tokens" in node and isinstance(
                node["cache_creation_input_tokens"], (int, float)
            ):
                cache_create += int(node["cache_creation_input_tokens"])
            if model is None and isinstance(node.get("model"), str):
                model = node["model"]
    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_input_tokens": cache_read,
        "cache_creation_input_tokens": cache_create,
        "turns": turns,
        "duration_ms": duration_ms,
    }


def pricing_tier(model: str | None) -> str:
    if not model:
        return "sonnet"
    name = model.lower()
    for tier in ("opus", "sonnet", "haiku"):
        if tier in name:
            return tier
    return "sonnet"


def estimate_cost_usd(stats: dict[str, Any]) -> float:
    tier = pricing_tier(stats.get("model"))
    rates = PRICING[tier]
    return (
        stats["input_tokens"] * rates["input"]
        + stats["output_tokens"] * rates["output"]
        + stats["cache_read_input_tokens"] * rates["cache_read"]
        + stats["cache_creation_input_tokens"] * rates["cache_write"]
    ) / 1_000_000


def render_markdown(stats: dict[str, Any], cost_usd: float) -> str:
    duration_s = stats["duration_ms"] / 1000 if stats["duration_ms"] else 0
    lines = [
        "### Claude review usage",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Model | `{stats['model'] or 'unknown'}` |",
        f"| Input tokens | {stats['input_tokens']:,} |",
        f"| Output tokens | {stats['output_tokens']:,} |",
        f"| Cache read | {stats['cache_read_input_tokens']:,} |",
        f"| Cache create | {stats['cache_creation_input_tokens']:,} |",
        f"| Turns | {stats['turns']} |",
        f"| Duration | {duration_s:.1f}s |",
        f"| API-equivalent cost (not billed) | ${cost_usd:.4f} |",
        "",
        "_OAuth/Pro-Max usage is quota-based; the cost is computed at public "
        "API list pricing as a stable comparison metric._",
        "",
    ]
    return "\n".join(lines)


def render_pr_footer(stats: dict[str, Any], cost_usd: float, run_url: str) -> str:
    model = stats["model"] or "unknown"
    return (
        "<!-- claude-cost-marker -->\n"
        f"> **Claude review usage** — model `{model}` · "
        f"in {stats['input_tokens']:,} · out {stats['output_tokens']:,} · "
        f"cache {stats['cache_read_input_tokens']:,} · "
        f"API-equivalent ~${cost_usd:.4f} (OAuth/Max quota, not billed) · "
        f"[Actions run]({run_url})"
    )


def append_step_summary(text: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a", encoding="utf-8") as fh:
        fh.write(text)
        if not text.endswith("\n"):
            fh.write("\n")


def main() -> int:
    out_path = Path(os.environ.get("CLAUDE_COST_OUT", "claude-cost.json"))
    pr_footer_path = Path(os.environ.get("CLAUDE_COST_PR_FOOTER", "claude-cost-pr-footer.md"))
    run_url = os.environ.get(
        "CLAUDE_RUN_URL",
        f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
        f"{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/"
        f"{os.environ.get('GITHUB_RUN_ID', '')}",
    )

    exec_file = find_execution_file()
    if exec_file is None:
        empty = {"available": False}
        out_path.write_text(json.dumps(empty), encoding="utf-8")
        append_step_summary(
            "### Claude review usage\n\n_Execution log not found; skipping cost report._\n"
        )
        return 0

    stats = collect_stats(exec_file)
    cost_usd = estimate_cost_usd(stats)
    payload = {
        "available": True,
        "workflow": os.environ.get("GITHUB_WORKFLOW", ""),
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "run_url": run_url,
        "pr_number": os.environ.get("CLAUDE_PR_NUMBER", "") or None,
        "tier": os.environ.get("CLAUDE_REVIEW_TIER", "") or None,
        "estimated_cost_usd": round(cost_usd, 6),
        **stats,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    pr_footer_path.write_text(render_pr_footer(stats, cost_usd, run_url), encoding="utf-8")
    append_step_summary(render_markdown(stats, cost_usd))
    return 0


if __name__ == "__main__":
    sys.exit(main())
