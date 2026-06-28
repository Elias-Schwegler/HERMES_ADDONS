# Hermes coder platform — supervised agentic coding

A two-tier system that lets you ask Hermes (on Telegram) to **build** something — not
just print code, but plan → test-drive → run → show you — with Hermes supervising a
specialist coder. Think: *you : Claude Code :: Hermes : OpenCode*, you supervising Hermes.

## Tiers
- **Manager — Hermes (Qwen, vision-capable).** Your proxy. Clarifies requirements,
  delegates, **reviews** the coder (catches stubs, enforces TDD), validates UIs by sight,
  presents the result. Does *not* write the code.
- **Coder — OpenCode + Ornith 1.0-35B (text).** Plans method-granularly, does TDD,
  self-recovers via tests, runs entirely inside an **isolated sandbox**.

## Pipeline (`hermes-coder` verbs)
```
 clarify (Hermes asks you)         → requirements
 new <p> "<goal>"                  → model up + sandbox + spec.md
 plan <p>                          → coder writes granular, test-first PLAN.md   (Hermes reviews)
 implement <p>                     → coder TDD loop until RESULT=PASS
 review <p>   [SUPERVISOR GATE]     → anti-stub (host, AST) + run suite (sandbox) → REVIEW=PASS
 ask <p> "<fix>"                   → Hermes feeds corrections back
 run <p>                           → role=run sibling container, app on 127.0.0.1:<port>
                                      web UIs: chromium screenshot → Qwen vision verdict
 present <p>                       → summary + localhost URL to the user
 finish <p> / gc                   → stop idle model, reap idle containers
```

## Components
| File | Role |
|---|---|
| `hermes-coder` | session orchestrator (the manager's interface) |
| `hermes-container` | bounded docker wrapper — every op fenced to `hermes-coder.managed=1` |
| `ornith-coder.service` | raw `llama-server` for Ornith (`--jinja` → clean OpenAI `tool_calls`) |
| `opencode.coder.json` | OpenCode → the raw llama-server (no LiteLLM, no Studio) |
| `AGENTS.md` | the coder's rules: method-granular, test-first, **no stubs** |
| `gates/check_no_stubs.py` | AST gate: stub bodies + fake `assert True` → FAIL |
| `vision/ui_check.py` | chromium screenshot + Qwen vision validation of UIs |
| `bench/` | the 10-problem regression benchmark |

## Why a raw llama-server (not Studio)
OpenCode sends OpenAI `tools`; Studio's chat endpoint **executes them itself** (host-side,
`tool_status`) — incompatible with an external harness. A raw `llama-server --jinja` returns
clean `tool_calls` that OpenCode runs **in our sandbox**. See [../docs/CODER_BACKEND.md](../docs/CODER_BACKEND.md).

## Security
- Sandbox = `hermes-coder-sandbox` image: **uid 1000, no host filesystem** (only `/work`),
  mem/cpu/pids-capped, `no-new-privileges`.
- hermesbot has **no direct docker** — only `hermes-container`/`hermes-coder` via sudoers.
- **No docker-in-docker.** Running an app uses a **host-orchestrated sibling** container with
  a **127.0.0.1-only** port (off-LAN). Model code never executes on the host.

## Validation status
- Phase 0–4 validated: clean `tool_calls`; OpenCode loop in sandbox; granular TDD PLAN.md +
  passing tests (roman_to_int, Stack); anti-stub gate (pass real / fail stubs);
  full `new→plan→implement→review` (Stack: 12/12, REVIEW=PASS); `runapp` + `127.0.0.1`
  reachability; chromium screenshot. UI vision-validate uses Ollama qwen3.6 vision.

## Install
`sudo bash install.sh`, then wire Hermes (see `hermes-skill-code.md`).
