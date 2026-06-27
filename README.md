# HERMES_ADDONS

Local-first AI stack addons for a **DGX Spark** (NVIDIA GB10 Blackwell, aarch64, CUDA 13)
running a personal **Hermes** Telegram agent. Everything runs **on-device** — no cloud APIs.

These are the glue pieces that make a pile of local tools behave like one coherent
assistant: a single OpenAI endpoint, on-demand model swapping, an agentic coding
sandbox, and media generation — all wired to the Hermes bot.

> ⚠️ **Public repo.** No secrets are committed. Real keys live in `.env` /
> `/etc/default/*` / the real config files, which are `.gitignore`d. Copy
> `.env.example` → `.env` and fill in your own. See **Security** below.

---

## How it sticks together

```
 Telegram ──► Hermes Agent Gateway ──► LiteLLM router (:4002, one OpenAI endpoint)
                                          │   routes by `model:` field, auto-fallback
            ┌─────────────────────────────┼───────────────────────────────────┐
            ▼                             ▼                                     ▼
   unsloth-autoreload-proxy        (coding tasks)                       Ollama (:11434)
   (:8889, "Ollama-style")     hermes coder platform                   variety models
            │ swaps model on             │                              (fallback / extras)
            │ demand, per request        ▼
            ▼                    OpenCode (headless harness)
   Unsloth Studio (:8888)   ──drives──►  Ornith 1.0-35B (coding model, via the proxy)
   one model at a time              │     runs INSIDE ▼
   + keepalive idle-unload          │     hermes-container sandbox (isolated, non-root,
                                     │       capped, no host FS) — code is built & run here
                                     ▼
                              Obsidian vault  ◄── persists solutions (reuse, don't recode)

 Media (via host ComfyUI :8188):  Krea 2 (t2i / img2img)  ·  NVIDIA PiD (4K upscale)  ·  ByteDance Lance
```

**The key trick:** Unsloth Studio only serves one model at a time, but
`unsloth-autoreload-proxy` makes it behave like Ollama — it inspects the request's
`model` field and **hot-swaps** Studio's loaded model, while `unsloth-keepalive`
idle-unloads it. So the generalist (Qwen 3.6 35B-A3B MTP) and the coding specialist
(Ornith) share one GPU footprint, swapped on demand. No Ollama needed for serving.

---

## Components

### `unsloth-stack/` — Ollama-style serving on top of Unsloth Studio
- **`unsloth-autoreload-proxy`** — OpenAI-compatible proxy (`:8889`). Curates a model
  list, and on each `/v1/*` request swaps Studio to the requested GGUF, then forwards.
- **`unsloth-keepalive`** — idle auto-unload daemon (frees the GPU when nothing's using it).
- **`unsloth-keepalive.env.example`** — config template (`EXPOSED_MODELS`, idle thresholds,
  `STUDIO_API_KEY`). Deploy as `/etc/default/unsloth-keepalive`.
- systemd units for both.

### `coder/` — agentic coding sandbox (the Hermes "code" specialist)
> ⚠️ **Status: planned / parked — see [docs/CODER_BACKEND.md](docs/CODER_BACKEND.md).**
> Ornith is registered + serving, but the OpenCode harness isn't wired live (Unsloth
> Studio's chat endpoint runs client tools *itself*, so it can't host an external
> harness while its chat tools stay on). These sandbox pieces are built and ready for
> the file-safe path (OpenCode + this container + a separate raw `llama-server`).

- **`hermes-container`** — a **bounded** docker lifecycle wrapper. hermesbot runs *only*
  this (via sudoers) and gets **no direct docker**: every op is fenced to containers
  labeled `hermes-coder.managed=1` — it can never touch ollama/litellm/comfyui/etc.
  Verbs: `create|start|stop|rm|exec|logs|list|deploy|gc`.
- **`Dockerfile.sandbox`** — the sandbox image (Python 3.12 + dev stack, **non-root**,
  no host mounts beyond `/work`, resource-capped).
- **`hermes-coder.sudoers`** — grants hermesbot exactly that one wrapper, nothing else.
- The coder (Ornith) runs through **OpenCode** (headless harness: plan → edit → run →
  read errors → fix) *inside* the sandbox, reaching the model via the proxy.

### `litellm/` — the single endpoint Hermes talks to
- **`config.example.yaml`** — model routes (generalist MTP, Ornith coding specialist via
  the proxy, Ollama fallbacks) + automatic fallback chains. Redacted; add your keys.

### `config/` — OpenCode harness config
- **`opencode.example.json`** — providers (unsloth proxy + ollama), model `limit` blocks
  (these enable OpenCode's **auto-compaction** so long sessions don't degrade).

### Media tools (documented; live in sibling repos/dirs)
- **Krea 2** (ComfyUI t2i + img2img), **NVIDIA PiD** (mem-capped 4K upscale container),
  **ByteDance Lance** (image/video) — see `docs/ARCHITECTURE.md`.

---

## Setup (sketch)
```bash
cp .env.example .env          # fill in YOUR keys
sudo bash coder/install.sh    # hermes-container wrapper + bounded sudoers
# deploy unsloth-stack/* to /usr/local/bin + /etc/default + /etc/systemd/system
# copy litellm/config.example.yaml → your litellm config dir, add keys
# copy config/opencode.example.json → ~/.config/opencode/opencode.json, add keys
```
A `hermes-stack-healthcheck` (see `docs/`) verifies every coupling after any tool update,
so you can update Unsloth Studio / OpenCode / llama.cpp **without losing custom features**.

## Security
- **No secrets in git.** `.gitignore` blocks `.env`, real configs, keys, `auth.db`, etc.
- **hermesbot is least-privilege:** no docker group; only the fenced `hermes-container`
  wrapper via sudoers; the sandbox is non-root with no host filesystem.
- Model-generated code only ever runs **inside** the sandbox container.

## License
MIT for the glue code here. Orchestrated models/tools carry their own licenses
(some non-commercial, e.g. PiD = NSCLv1). See `LICENSE`.
