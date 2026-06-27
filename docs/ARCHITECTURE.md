# Architecture

A local, on-device AI stack for the **Hermes** Telegram agent on a DGX Spark
(GB10 Blackwell, aarch64, CUDA 13). Design goals: one endpoint, on-demand model
swapping (lean GPU), a safe agentic coding sandbox, and update-resilience.

## Request flow
1. **Telegram → Hermes Agent Gateway** — the bot. Reads `~/.hermes/config.yaml`,
   talks to exactly one endpoint: the LiteLLM router.
2. **LiteLLM (`:4002`)** — single OpenAI-compatible endpoint. Routes by `model:`
   field, with automatic fallback chains.
3. **Serving** — two backends:
   - **Unsloth Studio (`:8888`) + `unsloth-autoreload-proxy` (`:8889`) + `unsloth-keepalive`.**
     Studio serves one model at a time; the proxy makes it act like Ollama by
     **hot-swapping** the loaded GGUF to match each request, and keepalive
     idle-unloads it. The generalist (Qwen 3.6 35B-A3B **MTP**) and the coding
     specialist (**Ornith 1.0 35B**) share one GPU footprint this way.
   - **Ollama (`:11434`)** — fallback + variety models only.

## Coding (the "code specialist")
> **Status: PARKED / planned — see [CODER_BACKEND.md](CODER_BACKEND.md).** Ornith is
> registered + serving today, but the OpenCode harness is **not wired live**: Studio's
> chat endpoint runs client-supplied tools *itself* (server-side, host-side), so it
> can't host an external harness while its chat tools stay on. The design + the two
> ways to finish it (Studio's own coder, or file-safe OpenCode on a separate
> `llama-server`) are captured in that doc. The sandbox pieces below are built and ready.

The intended design: a coding task is delegated to **OpenCode** (headless agentic
harness: plan → edit files → run → read errors → fix). OpenCode drives **Ornith** via
a raw `llama-server`, and runs **inside** a `hermes-container` sandbox:
- **Sandbox** = `hermes-coder-sandbox` image: Python 3.12 + dev stack, **non-root
  (uid 1000)**, **no host filesystem** (only `/work`), memory/cpu/pids capped.
- **`hermes-container`** = bounded docker wrapper. hermesbot has **no direct
  docker** — only this wrapper via sudoers, fenced to `hermes-coder.managed=1`
  containers (cannot touch ollama/litellm/comfyui/…). Verbs:
  `create|start|stop|rm|exec|logs|list|deploy|gc`.
- **Obsidian** = memory: solutions persist to the vault; the agent checks it first
  to reuse prior work instead of recoding. `deploy` pins a container (exempt from
  `gc`); `gc` reaps idle ephemeral ones.

## Context / not-going-dumb
- llama.cpp/Studio **hard-truncate** at `num_ctx` (no compaction).
- **OpenCode auto-compacts** — but only when each model's `limit` block (context +
  output) is set in `opencode.json`. Those blocks are the fix; without them
  compaction silently breaks and long sessions degrade.

## Media (via host ComfyUI `:8188`)
- **Krea 2** — text-to-image + image-to-image (NVFP4 on Blackwell), LoRA stack,
  optional uncensor rebalance node.
- **NVIDIA PiD** — fast 4K upscale, in a **memory-capped** container so it can't
  OOM-cascade the host.
- **ByteDance Lance** — image/video generation (isolated container).

## Update-safety
The whole custom layer lives **outside** the tool installs (`/usr/local/bin`,
`/etc/default`, `~/.config`, this repo), so updating Unsloth Studio / OpenCode /
llama.cpp doesn't delete it. The real coupling risk is **API drift** (the proxy
calls Studio's `/api/inference/*`); a post-update health-check pings every coupling
so breakage is caught immediately. Keep this repo as the source of truth: snapshot
→ update a tool → `git diff` → restore anything an update clobbers.

## Security
- No secrets in git (`.gitignore` + redacted `*.example` configs + `.env`).
- hermesbot is least-privilege (no docker group; one fenced wrapper).
- Model-generated code only ever executes **inside** the sandbox.
