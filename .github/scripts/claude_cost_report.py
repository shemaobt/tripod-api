"""Aggregate per-run Claude cost artifacts into a weekly rollup.

Inputs:
  - ``--artifacts-dir``: directory containing one ``claude-cost.json`` per run
    (downloaded by the cost-report workflow).
  - ``--lookback-days``: window the artifacts cover (used in the report header).
  - ``--repo``: ``owner/name`` of the repo, used in links.

Outputs:
  - ``--markdown-out``: a markdown summary appended to ``$GITHUB_STEP_SUMMARY``.
  - ``--discord-out``: a Discord webhook JSON payload (embed). The workflow
    only POSTs this if the ``DISCORD_WEBHOOK_URL`` secret is set, so a Discord
    target is opt-in.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

DISCORD_EMBED_COLOR = 0xCC785C  # Anthropic ochre


def load_artifacts(directory: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in directory.rglob("claude-cost.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or not data.get("available"):
            continue
        records.append(data)
    return records


def model_tier(model: str | None) -> str:
    if not model:
        return "unknown"
    m = model.lower()
    for tier in ("opus", "sonnet", "haiku"):
        if tier in m:
            return tier
    return "unknown"


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    total_cost = 0.0
    total_input = total_output = total_cache_read = total_cache_create = 0
    by_workflow: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"runs": 0, "cost": 0.0, "input": 0, "output": 0}
    )
    by_tier: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"runs": 0, "cost": 0.0, "input": 0, "output": 0}
    )
    top_runs: list[dict[str, Any]] = []

    for r in records:
        cost = float(r.get("estimated_cost_usd", 0) or 0)
        total_cost += cost
        total_input += int(r.get("input_tokens", 0) or 0)
        total_output += int(r.get("output_tokens", 0) or 0)
        total_cache_read += int(r.get("cache_read_input_tokens", 0) or 0)
        total_cache_create += int(r.get("cache_creation_input_tokens", 0) or 0)

        workflow = r.get("workflow") or "unknown"
        by_workflow[workflow]["runs"] += 1
        by_workflow[workflow]["cost"] += cost
        by_workflow[workflow]["input"] += int(r.get("input_tokens", 0) or 0)
        by_workflow[workflow]["output"] += int(r.get("output_tokens", 0) or 0)

        tier = model_tier(r.get("model"))
        by_tier[tier]["runs"] += 1
        by_tier[tier]["cost"] += cost
        by_tier[tier]["input"] += int(r.get("input_tokens", 0) or 0)
        by_tier[tier]["output"] += int(r.get("output_tokens", 0) or 0)

        top_runs.append(
            {
                "cost": cost,
                "model": r.get("model"),
                "pr_number": r.get("pr_number"),
                "run_url": r.get("run_url"),
                "tier": r.get("tier"),
                "input_tokens": int(r.get("input_tokens", 0) or 0),
                "output_tokens": int(r.get("output_tokens", 0) or 0),
            }
        )

    top_runs.sort(key=lambda x: x["cost"], reverse=True)

    return {
        "total_runs": len(records),
        "total_cost": total_cost,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cache_read": total_cache_read,
        "total_cache_create": total_cache_create,
        "by_workflow": dict(by_workflow),
        "by_tier": dict(by_tier),
        "top_runs": top_runs[:5],
    }


def render_markdown(summary: dict[str, Any], lookback_days: int, repo: str) -> str:
    lines = [
        f"## Claude PR review usage — last {lookback_days} day(s)",
        "",
    ]
    if summary["total_runs"] == 0:
        lines.append("_No Claude review runs in the lookback window._")
        return "\n".join(lines) + "\n"

    lines += [
        f"- **Total runs:** {summary['total_runs']}",
        f"- **Estimated cost (API equivalent):** ${summary['total_cost']:.4f}",
        f"- **Tokens:** {summary['total_input_tokens']:,} in · "
        f"{summary['total_output_tokens']:,} out · "
        f"{summary['total_cache_read']:,} cache-read · "
        f"{summary['total_cache_create']:,} cache-create",
        "",
        "### By model tier",
        "| Tier | Runs | Cost | Input | Output |",
        "|---|---|---|---|---|",
    ]
    for tier in ("opus", "sonnet", "haiku", "unknown"):
        if tier not in summary["by_tier"]:
            continue
        s = summary["by_tier"][tier]
        lines.append(
            f"| {tier} | {s['runs']} | ${s['cost']:.4f} | {s['input']:,} | {s['output']:,} |"
        )
    lines += [
        "",
        "### By workflow",
        "| Workflow | Runs | Cost |",
        "|---|---|---|",
    ]
    for name, s in sorted(summary["by_workflow"].items()):
        lines.append(f"| {name} | {s['runs']} | ${s['cost']:.4f} |")

    if summary["top_runs"]:
        lines += [
            "",
            "### Top runs by cost",
            "| Cost | Model | Tier | PR | Run |",
            "|---|---|---|---|---|",
        ]
        for r in summary["top_runs"]:
            pr = f"#{r['pr_number']}" if r["pr_number"] else "—"
            run_link = f"[run]({r['run_url']})" if r["run_url"] else "—"
            tier_str = r["tier"] or "—"
            model_str = r["model"] or "—"
            lines.append(f"| ${r['cost']:.4f} | `{model_str}` | {tier_str} | {pr} | {run_link} |")

    lines += [
        "",
        f"_Repo: `{repo}`. Pricing computed at public Anthropic API list rates "
        f"as a stable comparison metric — actual OAuth/Pro-Max usage is quota-based._",
        "",
    ]
    return "\n".join(lines)


def render_discord(summary: dict[str, Any], lookback_days: int, repo: str) -> dict[str, Any]:
    if summary["total_runs"] == 0:
        return {
            "username": "Claude Cost Report",
            "embeds": [
                {
                    "title": f"Claude PR review usage — last {lookback_days} day(s)",
                    "description": "_No Claude review runs in the lookback window._",
                    "color": DISCORD_EMBED_COLOR,
                }
            ],
        }

    fields: list[dict[str, Any]] = [
        {
            "name": "Totals",
            "value": (
                f"**{summary['total_runs']}** runs · "
                f"**${summary['total_cost']:.4f}** API-equivalent\n"
                f"{summary['total_input_tokens']:,} in · "
                f"{summary['total_output_tokens']:,} out · "
                f"{summary['total_cache_read']:,} cache-read"
            ),
            "inline": False,
        }
    ]

    tier_lines = []
    for tier in ("opus", "sonnet", "haiku", "unknown"):
        if tier not in summary["by_tier"]:
            continue
        s = summary["by_tier"][tier]
        tier_lines.append(f"`{tier}` — {s['runs']} runs · ${s['cost']:.4f}")
    if tier_lines:
        fields.append({"name": "By model tier", "value": "\n".join(tier_lines), "inline": True})

    workflow_lines = [
        f"`{name}` — {s['runs']} runs · ${s['cost']:.4f}"
        for name, s in sorted(summary["by_workflow"].items())
    ]
    if workflow_lines:
        fields.append({"name": "By workflow", "value": "\n".join(workflow_lines), "inline": True})

    if summary["top_runs"]:
        top_lines = []
        for r in summary["top_runs"]:
            pr = f"PR #{r['pr_number']}" if r["pr_number"] else "—"
            link = f"[run]({r['run_url']})" if r["run_url"] else ""
            tier_str = r["tier"] or "?"
            top_lines.append(
                f"${r['cost']:.4f} · `{r['model'] or '?'}` ({tier_str}) · {pr} {link}".strip()
            )
        fields.append({"name": "Top runs", "value": "\n".join(top_lines), "inline": False})

    return {
        "username": "Claude Cost Report",
        "embeds": [
            {
                "title": f"Claude PR review usage — last {lookback_days} day(s)",
                "description": f"Repo: `{repo}`",
                "color": DISCORD_EMBED_COLOR,
                "fields": fields,
                "footer": {
                    "text": "OAuth/Pro-Max is quota-based; cost is API list-price equivalent."
                },
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    parser.add_argument("--lookback-days", required=True, type=int)
    parser.add_argument("--markdown-out", required=True, type=Path)
    parser.add_argument("--discord-out", required=True, type=Path)
    parser.add_argument("--repo", required=True)
    args = parser.parse_args()

    records = load_artifacts(args.artifacts_dir)
    summary = summarize(records)

    args.markdown_out.write_text(
        render_markdown(summary, args.lookback_days, args.repo), encoding="utf-8"
    )
    args.discord_out.write_text(
        json.dumps(render_discord(summary, args.lookback_days, args.repo), indent=2),
        encoding="utf-8",
    )
    print(f"Aggregated {summary['total_runs']} run(s) totalling ${summary['total_cost']:.4f}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
