# haiku-crew

A Claude Code plugin for running Opus as the orchestrator and Haiku as the workers. Based on the r/ClaudeAI thread "How much more effective is Opus 5.5 w/ Haiku subagents than just Opus 5.5".

The thread agreed on three things, and each one maps to a part of this plugin:

| Thread finding | What the plugin does |
| --- | --- |
| Haiku is cheap and holds up on **scoped** work (one file plus a check), and drifts on open-ended chunks | Four Haiku agents with rigid contracts, turn caps, and a required report format |
| Opus often spawns subagents on **its own model**, and CLAUDE.md rules get ignored | A `PreToolUse` hook blocks generic subagents that leave `model` unset |
| Savings come from keeping reads in the worker's context, and from splitting work **by code area**, not by task | A delegation policy injected at every session start (and after `/clear` and compaction) |

## What's inside

```
haiku-crew/
├── .claude-plugin/plugin.json
├── agents/
│   ├── scout.md        read-only search          haiku, effort medium
│   ├── runner.md       tests/lint/build, failures only   haiku, effort low
│   ├── implementer.md  one bounded edit + check  haiku, effort high
│   └── checker.md      verify against criteria   haiku, effort high
├── hooks/hooks.json    SessionStart → policy.md, PreToolUse(Agent) → gate
├── policy.md           the delegation rules the main thread sees
└── scripts/agent_gate.py
```

**The gate.** These spawns are blocked: `general-purpose`, `claude`, `Explore`, `Plan`, or no type at all, when `model` is unset. The model gets a message pointing it at the right worker, or telling it to retry with `model: "haiku"` (or `"opus"` for genuinely hard subtasks). These pass untouched: the `haiku-crew:*` agents, your own custom agents (they carry their own `model` frontmatter), and forks. A blocked spawn costs one extra short turn.

**The audit log.** Every Agent call, allowed or blocked, is appended to `delegations.jsonl` in the plugin's data directory. That answers "is it actually delegating?" with data rather than vibes.

## Install

Needs Claude Code with plugin support and [`uv`](https://docs.astral.sh/uv/) on your PATH. The gate is a standard-library-only Python script run with `uv run --script`. If `uv` is missing, the hook fails open and you'll see a hook error notice.

**Try it for one session:**

```bash
claude --plugin-dir ~/path/to/haiku-crew
```

**Load it in every session** (no marketplace needed): put the folder in your personal skills directory, then run `/reload-plugins` or start a new session.

```bash
mkdir -p ~/.claude/skills && unzip haiku-crew.zip -d ~/.claude/skills/
```

Check it loaded: `claude plugin list`, or ask Claude which `haiku-crew:` agents it has.

## Use

Mostly you don't do anything: the policy and descriptions route work automatically. A few prompts that work well:

- `Plan this in plan mode and label each step with its owner.`
- `@"haiku-crew:scout (agent)" where do we handle sprite collision?`
- `Implement steps 2–4 with implementer workers, one per area, then send checker over each diff.`

## Tune it

- **Opus effort.** One tester in the thread found Opus 5.5 at **medium** driving Haiku 5.5 at **high** to be the sweet spot. Set your session effort with `/effort` or in settings; the workers set their own via `effort:` frontmatter.
- **Turn the gate off** for a session: `HAIKU_CREW_GATE=off claude`. Logging keeps running.
- **Force every subagent onto Haiku** (blunt, overrides everything including the `opus` escape hatch): set `CLAUDE_CODE_SUBAGENT_MODEL=haiku` and `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` in the `env` block of `~/.claude/settings.json`.
- **Project conventions.** `scout` and `runner` skip CLAUDE.md files (`omitClaudeMd: true`) to stay lean, so the brief has to name commands and paths. `implementer` and `checker` load your CLAUDE.md so they follow project conventions.

## Audit

```bash
f=$(find ~/.claude/plugins/data -path '*haiku-crew*' -name delegations.jsonl | head -1)
jq -r '[.type, .model, (if .blocked then "BLOCKED" else "ok" end)] | @tsv' "$f" | sort | uniq -c | sort -rn
```

Watch the ratio of `haiku-crew:*` calls to blocked ones. If blocks stay high after a few sessions, the policy wording needs tightening for your workflow. Run `/tasks` while a subagent runs to see which model it's actually on.

## Caveats

- Haiku is the right worker only when the brief is tight. If a task can't be described as goal + files + check, keep it on the main thread.
- Parallel workers cost usage too. Your main context staying small doesn't mean the session was cheap; check total usage against your limit reset.
