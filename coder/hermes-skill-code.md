# Skill: `/code` — delegate coding to the Ornith coder (supervised)

When the user asks you to build/code something (or types `/code <task>`), **you
(Hermes/Qwen, the manager) do NOT write the code yourself.** You drive the Ornith
coding agent via `hermes-coder` and **supervise** it. You are the user's proxy *and*
the coder's reviewer — like a senior engineer directing a junior and checking every PR.

## Workflow
1. **Clarify** — ask the user 1–3 sharp questions to pin requirements (inputs/outputs,
   acceptance criteria, is there a UI?, what data?). Keep it short; then proceed.
2. **Start** — `sudo hermes-coder new <proj> "<clear goal + acceptance criteria>"`
3. **Plan** — `sudo hermes-coder plan <proj>` (coder writes a granular `PLAN.md`).
   - **Read the plan.** If it's not method-granular (whole classes at once) or misses a
     requirement → `sudo hermes-coder ask <proj> "<correct the plan: ...>"` and re-plan.
4. **Build** — `sudo hermes-coder implement <proj>` (coder does TDD until `RESULT=PASS`).
5. **Review (mandatory supervision)** — `sudo hermes-coder review <proj>`
   - `REVIEW=PASS` only if **no stubs** *and* the **suite is green**.
   - On `REVIEW=FAIL`: read the reason, then `sudo hermes-coder ask <proj> "<specific fix>"`
     and re-implement/review. Watch for stub-dubs / fake tests — the gate catches them,
     but also eyeball the code yourself.
6. **Run** — `sudo hermes-coder run <proj>` (runs it; web apps get a `127.0.0.1:<port>` URL).
   - For UIs the run does a **vision check** (your eyes — the coder is blind to its own UI).
     If it reports `UI=ISSUES`, `ask` the coder to fix and re-run.
7. **Present** — `sudo hermes-coder present <proj>` → summarize to the user + give the URL.
8. **Finish** — `sudo hermes-coder finish <proj>` → frees the model when idle.

## Rules
- **Never present unreviewed code.** `REVIEW=PASS` is required before `run`/`present`.
- If the coder is stuck (`RESULT=BLOCKED`) after ~2 corrections, tell the user what's blocking.
- All code runs **only in the sandbox** — never run the coder's output on the host.

## Integration (one-time, host)
- Add `hermes-coder` to Hermes' `command_allowlist` (so the manager may call it without prompting).
- Install this file as a Hermes skill (e.g. `~/.hermes/skills/code.md`) and register `/code`.
