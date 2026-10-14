#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""PreToolUse gate for the Agent tool.

Blocks generic subagent spawns (general-purpose, claude, Explore, Plan, or no
type) that leave `model` unset, because those silently run on the main
conversation's model. Named agents (haiku-crew:*, your own custom agents) and
forks pass through. Every Agent call is logged to delegations.jsonl so you can
audit what actually got delegated.

Set HAIKU_CREW_GATE=off to disable blocking (logging continues).
"""
import json
import os
import sys
import time

GENERIC = {"", "general-purpose", "claude", "explore", "plan"}


def log(entry):
    data_dir = os.environ.get("CLAUDE_PLUGIN_DATA")
    if not data_dir:
        return
    try:
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, "delegations.jsonl"), "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def main():
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # not our problem; let the normal flow continue

    tool_input = event.get("tool_input") or {}
    agent_type = (tool_input.get("subagent_type") or "").strip()
    model = (tool_input.get("model") or "").strip()
    generic = agent_type.lower() in GENERIC
    blocked = generic and not model and os.environ.get("HAIKU_CREW_GATE") != "off"

    log({
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "session": event.get("session_id"),
        "cwd": event.get("cwd"),
        "type": agent_type or "(none)",
        "model": model or "(default)",
        "description": tool_input.get("description", ""),
        "blocked": blocked,
    })

    if not blocked:
        return 0

    reason = (
        f"haiku-crew: a '{agent_type or 'general-purpose'}' subagent without a model "
        "runs on the main conversation's model. For search use haiku-crew:scout; for "
        "tests/lint/build haiku-crew:runner; for a scoped edit haiku-crew:implementer; "
        "for verification haiku-crew:checker. To keep this subagent type, call Agent "
        "again with model set: \"haiku\" for bounded work, \"opus\" only when the subtask "
        "needs design or deep reasoning."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
