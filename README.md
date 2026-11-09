# KynAI

A terminal-first, multi-agent incident investigator. Run it inside a codebase, bring your own API key (Claude, OpenAI, or any OpenAI-compatible endpoint), describe the incident, and get a root-cause report with file-and-line evidence.

> **Status:** rebuild in progress. The previous FastAPI data-analysis chatbot is preserved at tag `legacy-chatbot`.
>
> **Honesty line:** personal project, synthetic incident data, evaluated with fault injection. Separate from my production work at Aviara.

## Target usage

```bash
pipx install kynai
kynai init      # pick a provider; the key goes into the OS keychain
kynai investigate "pricing worker crashes every few hours since Friday" --logs ./logs --since 3d
```

Output: `kynai-reports/<date>-<slug>.md` with summary, timeline, ranked hypotheses with confidence, evidence (file:line, commit hashes, log excerpts), suggested fix as a diff, and what was not checked.

## Architecture (planned)

- **CLI:** Typer + Rich live progress
- **Providers:** one OpenAI-compatible client + native Anthropic adapter (swappable to Switchboard by config)
- **Agent graph (LangGraph):** Planner → Code explorer / Change analyst / Log+metrics analyst → RCA synthesizer → Critic → Human approval gate
- **Agentic RAG over code:** repo map + tree-sitter symbol index, on-demand chunk retrieval, per-run token budget
- **MCP both ways:** client of `observability-mcp` / `deploy-mcp`; server via `kynai mcp serve`
- **Sessions:** SQLite (`kynai history`, `kynai resume`)

## Repo layout

| Path | Purpose |
|---|---|
| `src/kynai/` | CLI, agents, providers, tools |
| `mcp/observability-mcp`, `mcp/deploy-mcp` | MCP servers I build (Python, official SDK) |
| `demo-target/` | RMS-style service with seeded faults (one git branch per fault) |
| `evals/golden/` | 30–40 golden incidents with known root cause, file, commit |
| `docs/` | Design doc, case study draft |
| `bench/` | Raw eval and ablation results exported from LangSmith (traces expire after 14 days) |

## Milestones (2 weeks, Nov 10 – Nov 23)

1. Days 1–3: CLI skeleton, provider layer, read-only repo tools, single-agent investigation end to end
2. Days 4–7: multi-agent graph, critic, approval prompts, report writer, codebase RAG
3. Days 8–10: fault-injection target, golden set, `kynai eval` + LangSmith, ablations
4. Days 11–14: MCP client + server, PyPI release, Azure Container Apps demo stack, case study, 2-minute recording

## Part of a larger platform

KynAI is one of four connected projects: [Switchboard](../Switchboard) (LLM gateway), [RevSQL](../RevSQL) (fine-tuned text-to-SQL), [Relay](../Relay) (event delivery). Model calls move to Switchboard by config; reports leave through Relay.
