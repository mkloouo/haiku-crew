# Delegation setup (haiku-crew plugin)

This user runs Claude Code as one orchestrator plus cheap Haiku workers. The main thread plans, decides and integrates. Bounded grunt work goes to Haiku subagents, whose file reads and command output stay in their own context, so only a short report comes back here.

## Who does what

- **Main thread**: planning, architecture, root-cause debugging, core domain logic, anything that needs the whole picture, reviewing worker results, talking to the user.
- **haiku-crew:scout**: find files, symbols, call sites, config, "where/how is X done". Use it instead of Explore or reading many files here.
- **haiku-crew:runner**: run tests, lint, typecheck, build; summarize logs. Returns only the failures.
- **haiku-crew:implementer**: one bounded change: a few named files plus a check command that proves it works.
- **haiku-crew:checker**: verify a change against acceptance criteria. Pair it with implementer (writer, then checker).

## Working rules

1. **Small stuff stays inline.** A single grep, one file read, or a one-line edit is cheaper here than a spawn.
2. **Briefs are contracts.** Workers see none of this conversation. Every brief gives: Goal, Files (exact paths; for implementer, the only files it may edit), Check (the command that proves done), Out of scope, and any conventions or commands they need. Vague briefs are where Haiku drifts.
3. **Split by code area, not by task.** Workers that search the same area each pay for the same reads. One worker per area; never give two implementers overlapping files.
4. **Pick the model on purpose.** The haiku-crew workers already run on Haiku. A generic subagent (general-purpose, claude, Explore, Plan) needs an explicit `model`: `haiku` by default, `opus` only for a subtask that needs design or deep reasoning. Sonnet is not used unless the user asks. A hook blocks generic spawns that leave `model` unset.
5. **A worker's DONE is a claim, not proof.** Read its check output, or send runner/checker to confirm before building on it.
6. **BLOCKED or FAILED means re-scope.** Narrow the brief or take the task back. Do not resend the same brief. After two failures on one task, do it on the main thread.
7. **In plan mode**, label each step with its owner (`main`, `scout`, `runner`, `implementer`, `checker`) and mark which steps can run in parallel.
