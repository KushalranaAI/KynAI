# KynAI design doc

*One page. Written before the code. Update as decisions change.*

## Problem
On-call engineers lose time correlating code, git history, logs and metrics during an incident. KynAI automates the investigation and produces evidence-backed root-cause reports.

## Constraints
- Must work on repos far larger than the context window
- Must never send secrets to the model; read-only by default
- Bring-your-own-key; must work with hosted and local models
- Per-run step limit and cost budget

## Decisions

| Decision | Choice | Rejected | Why |
|---|---|---|---|
| Orchestration | LangGraph | Hand-rolled loop | _TBD: fill in after building_ |
| Code context | Repo map + tree-sitter index + on-demand retrieval | Stuff files in prompt | Scales past context window |
| Safety | Command allowlist + human approval | Sandboxed code execution | Old chatbot's unsandboxed Python REPL is exactly what this must prevent |
| Key storage | OS keychain / env vars | Config files | Keys never land on disk in plaintext |
| Sessions | SQLite | Files | `history` / `resume` need queries |

## Open questions
- _TBD_

## Results (fill after measuring)
See `bench/`.
