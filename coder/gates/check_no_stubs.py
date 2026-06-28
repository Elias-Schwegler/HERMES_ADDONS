#!/usr/bin/env python3
"""Anti-stub + test-quality gate for the Hermes coder loop.

Run inside a project dir. Exit 0 = clean; non-zero = violations (printed).
This is the *mechanical* supervisor check (the model cannot talk its way past it):
catches stub bodies, leftover TODOs, missing tests, and fake/trivial assertions —
the "stub-dub" failure mode. Pair with actually running the suite (done by the
hermes-coder wrapper) for the full TDD gate.
"""
import ast, sys, os, re

SKIP = (".npm", ".cache", ".config", ".local", "__pycache__", ".git", "node_modules")

def _strip_docstring(body):
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
       and isinstance(body[0].value.value, str):
        return body[1:]
    return body

def is_stub_body(body):
    stmts = _strip_docstring(body)
    if not stmts:
        return True
    if len(stmts) == 1:
        s = stmts[0]
        if isinstance(s, ast.Pass):
            return True
        if isinstance(s, ast.Expr) and isinstance(getattr(s, "value", None), ast.Constant) and s.value.value is Ellipsis:
            return True
        if isinstance(s, ast.Raise):
            exc = s.exc
            name = None
            if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
                name = exc.func.id
            elif isinstance(exc, ast.Name):
                name = exc.id
            if name in ("NotImplementedError", "NotImplemented"):
                return True
    return False

def collect():
    src, test = [], []
    for root, _, files in os.walk("."):
        if any(p in root.split(os.sep) for p in SKIP):
            continue
        for fn in files:
            if fn.endswith(".py"):
                p = os.path.join(root, fn)
                (test if "test" in fn.lower() else src).append(p)
    return src, test

def main():
    src, test = collect()
    v = []

    for p in src:
        try:
            tree = ast.parse(open(p, encoding="utf-8", errors="ignore").read())
        except SyntaxError as e:
            v.append(f"{p}: syntax error: {e}"); continue
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and is_stub_body(n.body):
                v.append(f"{p}:{n.lineno}: stub function '{n.name}' (pass/.../NotImplementedError)")

    for p in src + test:
        for i, line in enumerate(open(p, encoding="utf-8", errors="ignore"), 1):
            m = re.search(r"\b(TODO|FIXME|XXX)\b", line)
            if m:
                v.append(f"{p}:{i}: leftover {m.group()}")

    if not test:
        v.append("no test files found — TDD requires tests that exercise the code")
    for p in test:
        try:
            tree = ast.parse(open(p, encoding="utf-8", errors="ignore").read())
        except SyntaxError as e:
            v.append(f"{p}: syntax error: {e}"); continue
        asserts = [n for n in ast.walk(tree) if isinstance(n, ast.Assert)]
        real = [a for a in asserts if not (isinstance(a.test, ast.Constant) and a.test.value is True)]
        # unittest uses self.assertEqual/...; pytest/scripts use plain `assert`. Accept either.
        # Top-level asserts (run via `python3 test_x.py`) count — no test_* function required.
        assertmethods = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr.startswith("assert")]
        if not asserts and not assertmethods:
            v.append(f"{p}: no assertions found — test doesn't verify anything")
        elif asserts and not real and not assertmethods:
            v.append(f"{p}: only trivial 'assert True' — tests don't verify behavior")

    if v:
        print("ANTI-STUB GATE: FAIL")
        for x in v:
            print("  -", x)
        return 1
    print(f"ANTI-STUB GATE: PASS ({len(src)} src, {len(test)} test files; no stubs, real assertions present)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
