# Coder backend — status, finding & decision (the "code specialist")

> **Status: Option A CONFIRMED WORKING (2026-06-28) — 10/10 coding benchmark passed.**
> The agentic coder loop runs via Studio's own built-in coder. Option B (isolated)
> remains built-but-not-wired, for untrusted autonomous work. This records the
> finding + both paths so nobody re-investigates from scratch. Last updated 2026-06-28.
>
> **Benchmark:** `coder/bench/bench.py` drove Studio's agentic coder (Ornith +
> `enable_tools`) on 10 problems (is_prime, merge_intervals, two_sum, valid_parens,
> fibonacci, binary_search, word_count, reverse_words, gcd, flatten). Each solution
> was **independently verified** (our own asserts run against the model's file, not
> its self-report): **10/10 PASS**, ~25 s/problem. Results: `coder/bench/RESULTS-2026-06-28.log`.

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

## The decision — Option A (in use), Option B (for untrusted work)
Studio chat tools stay **ON**. The lean agentic loop is **Option A**, now validated:

- **Option A — Studio's own agentic coder. ✅ CONFIRMED WORKING (10/10 benchmark).**
  POST `127.0.0.1:8888/v1/chat/completions` with `enable_tools:true` + Ornith loaded
  → it writes a file, runs `python3`, loops/fixes in `~/studio_sandbox` until correct.
  Lean: **no LiteLLM, no OpenCode**. ❌ host-side sandbox — can touch your files (see
  above), so keep it to trusted/benign tasks.
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
