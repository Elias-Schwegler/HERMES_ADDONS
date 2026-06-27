# Coder backend — status, finding & decision (the "code specialist")

> **Status: PARKED (design captured, pieces built — not wired live).**
> This records *why*, what was found, and the two ways to finish it, so nobody
> re-investigates from scratch. Last updated 2026-06-27.

## Goal
Let the generalist Hermes model delegate coding tasks to a specialist
(**Ornith 1.0-35B**, serving via the Unsloth stack), with generated code run in a
sandbox that **cannot touch the host's files**, and prior work persisted to
Obsidian (check-first, don't recode).

## The blocker — Unsloth Studio's endpoint is an *application* backend, not a raw model server
Studio's `/v1/chat/completions` behaves two completely different ways depending on
whether the client sends OpenAI `tools`:

| Request | Studio's behavior | Works for… |
|---|---|---|
| **No `tools`** (plain chat) | Clean OpenAI passthrough (standard `choices`/`delta` chunks) | **Hermes** — its skills are gateway-driven; it never sends OpenAI tools ✅ |
| **With `tools`** (agentic harness) | Studio **runs the tools itself**, server-side, in `~/studio_sandbox/<session>` as user `elias`, and streams non-OpenAI `{"type":"tool_status",…}` events | breaks external harnesses ❌ |

**This is why Hermes works and OpenCode doesn't.** OpenCode sends `tools` (that's
how it's an agent), which trips Studio's own agentic layer: the model's `bash`
executed on the **host** (created `~/studio_sandbox/_default/hello.py` as `elias`),
and OpenCode's strict ai-sdk parser rejected the `tool_status` chunk
(`Type validation failed … expected "choices" array`).

### There *is* a clean passthrough path — but it's gated
`studio/backend/routes/inference.py` has `_openai_passthrough_stream` (returns
standard `tool_calls` unmodified). It is used only when:
```
using_gguf  AND  not _effective_enable_tools(payload)  AND  (client sent tools / tool messages)
```
- `_effective_enable_tools()` (line ~1158) = a **process-level tool policy**
  (hard override from `unsloth run`) if set, else the per-request `enable_tools` field.
- Also requires `llama_backend.supports_tools` (Studio suppresses this for some templates).

Sending `enable_tools:false` in a single request did **not** flip it (the policy
and/or `supports_tools` won — confirmed by test: still emitted `tool_status`,
0 `tool_calls`). Forcing passthrough would mean changing Studio's launch / tool
policy globally — which **disables the agentic tools used in Studio chat**. Those
are wanted ON. **→ OpenCode cannot share Studio's endpoint.**

## Is Studio's own sandbox safe? (`~/studio_sandbox`)
Hardened, but **not a real jail** (`studio/backend/core/inference/tools.py`):
- ✅ repoints `HOME` (hides `~/.config`/`~/.cache` creds), strips credential env vars,
  rlimits (8 GB / CPU cap), cwd locked to `~/studio_sandbox/<session>`.
- ❌ **No uid/mount namespace** (code: "out of scope"). It runs as `elias`, so commands
  using **absolute paths** can still read/write real files (`/home/elias/…`, Obsidian, `~/.ssh`).

## The decision
Studio chat tools stay **ON** → the coder is parked. Two ways to finish it later:

- **Option A — Studio's own agentic coder.** One place, nothing new (Studio chat
  *is* a coding agent). ❌ host-side sandbox — can touch your files (see above).
- **Option B — file-safe OpenCode.** OpenCode + the isolated `hermes-container`
  (uid 1000, **no host FS**) + a **separate raw `llama-server`** for Ornith (the
  same llama.cpp engine Studio spawns, minus the agentic wrapper → clean
  `tool_calls`). ❌ a second endpoint (not "one place"). Pieces already built:
  `coder/hermes-container`, `coder/Dockerfile.sandbox`, `coder/hermes-coder.sudoers`.

## Current state (live now)
- Networking is the **original** `127.0.0.1` (proxy + LiteLLM). The `172.17.0.1`
  proxy bind the container path needed was **rolled back** (not needed without B).
- **Ornith is registered + serving** via the Unsloth stack: proxy `EXPOSED_MODELS`
  + LiteLLM route `unsloth-ornith-35b` (→ proxy → Studio). It idle-unloads
  (keepalive `EXTERNAL_IDLE=600s`). Spin up / take down / update anytime.
- OpenCode updated to **1.17.11**; `opencode.json` has the `limit` blocks (compaction fix).
