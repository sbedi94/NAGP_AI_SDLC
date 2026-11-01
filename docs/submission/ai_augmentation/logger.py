#!/usr/bin/env python3
"""Append-only AI augmentation logger for the AI-in-SDLC assignment."""
from __future__ import annotations

import argparse
import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOG = Path(__file__).resolve().parent / "ai-activity.jsonl"


def git_value(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True,
            text=True, check=True
        )
        return result.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def git_changed_files() -> list[str]:
    value = git_value("status", "--short")
    return value.splitlines() if value else []


def append_record(record: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Log an AI-assisted engineering activity.")
    parser.add_argument("--stage", required=True)
    parser.add_argument("--tool", default="ChatGPT")
    parser.add_argument("--model", default="GPT-6")
    parser.add_argument("--mode", required=True, choices=["ask", "plan", "agent", "edit", "combination"])
    parser.add_argument("--prompt", required=True, help="Actual prompt or a faithful concise record of it.")
    parser.add_argument("--response-summary", default="")
    parser.add_argument("--status", default="proposed",
                        choices=["proposed", "applied", "rejected", "partial", "rework", "validated", "failed"])
    parser.add_argument("--human-decision", default="")
    parser.add_argument("--validation", default="")
    parser.add_argument("--files-read", nargs="*", default=[])
    parser.add_argument("--files-modified", nargs="*", default=[])
    parser.add_argument("--tools-used", nargs="*", default=[])
    parser.add_argument("--skills-used", nargs="*", default=[])
    parser.add_argument("--mcp-tools-used", nargs="*", default=[])
    parser.add_argument("--evidence", nargs="*", default=[])
    parser.add_argument("--limitation", default="")
    parser.add_argument("--session-id", default="assignment-session-001")
    args = parser.parse_args()

    record = {
        "id": "AI-" + uuid.uuid4().hex[:12].upper(),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "session_id": args.session_id,
        "stage": args.stage,
        "agent": "assistant",
        "agent_name": args.tool,
        "agent_type": "built-in",
        "ai_tool": args.tool,
        "model": args.model,
        "mode": args.mode,
        "repository": ROOT.name,
        "git_branch": git_value("branch", "--show-current"),
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_working_tree": git_changed_files(),
        "context": "AI in SDLC workshop assignment",
        "request": args.prompt,
        "response_summary": args.response_summary,
        "skills_used": args.skills_used,
        "subagents_used": [],
        "mcp_tools_used": args.mcp_tools_used,
        "tools_used": args.tools_used,
        "files_read": args.files_read,
        "files_modified": args.files_modified,
        "human_decision": args.human_decision or None,
        "action_verification": args.validation or None,
        "evidence": args.evidence,
        "limitation": args.limitation or None,
        "status": args.status,
        "artifacts": args.files_modified,
    }
    append_record(record)
    print(f"Recorded {record['id']} in {LOG}")
    print(f"Git branch: {record['git_branch'] or 'unknown'}")
    print(f"Git commit: {record['git_commit'] or 'unknown'}")


if __name__ == "__main__":
    main()
