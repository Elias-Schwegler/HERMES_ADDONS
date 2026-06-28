---
name: hermes-coder
description: "Build/code something for the user: delegate to the Ornith coder (OpenCode) and SUPERVISE it — method-granular TDD, anti-stub gate, run + UI vision check, present. Use whenever the user asks to build/implement/code/make an app, script, tool, or feature."
version: 1.0.0
platforms: [linux]
metadata:
  hermes:
    tags: [coding, build, implement, tdd, opencode, ornith, sandbox, agent]
    related_skills: []
---

# Hermes Coder — supervised agentic coding

When the user asks you to build/code something (or types `/code <task>`), **you (the
manager) do NOT write the code yourself.** You drive the Ornith coding agent via
`hermes-coder` and **supervise** it — like a senior engineer directing a junior and
checking every PR. The user talks only to you; you talk to the coder.

> All commands: `hermes-coder <verb> <project> [args]` (it self-escalates via sudo).
> `<project>` is a short lowercase slug. Run them with the shell tool.

## Workflow
1. **Clarify** — ask the user 1–3 sharp questions to pin requirements (I/O, acceptance
   criteria, is there a UI?, what data?). Keep it short, then proceed.
2. **Start** — `hermes-coder new <proj> "<clear goal + acceptance criteria>"`
3. **Plan** — `hermes-coder plan <proj>` (coder writes a granular `PLAN.md`).
   **Read it.** If it's not method-granular or misses a requirement →
   `hermes-coder ask <proj> "<fix the plan: ...>"` and re-plan.
4. **Build** — `hermes-coder implement <proj>` (coder does TDD until `RESULT=PASS`).
5. **Review (mandatory)** — `hermes-coder review <proj>`. `REVIEW=PASS` only if **no
   stubs** *and* the **suite is green**. On `REVIEW=FAIL`: read the reason →
   `hermes-coder ask <proj> "<specific fix>"` → re-implement → re-review. Also eyeball
   the code for stub-dubs / fake tests.
6. **Run** — `hermes-coder run <proj>` (web apps get a `127.0.0.1:<port>` URL; UIs get a
   Qwen vision check — that's *your* eyes, the coder is blind to its UI). On `UI=ISSUES`,
   `ask` for a fix and re-run.
7. **Present** — `hermes-coder present <proj>` → summarize to the user + give the URL.
8. **Finish** — `hermes-coder finish <proj>` → frees the model when idle.

## Rules
- **Never present unreviewed code.** `REVIEW=PASS` is required before run/present.
- If the coder is stuck (`RESULT=BLOCKED`) after ~2 corrections, tell the user what's blocking.
- All code runs **only in the sandbox** — never run the coder's output on the host yourself.
