#!/usr/bin/env python3
"""UI vision check — the manager's eyes for the coder.

Ornith (the coder) is text-only, so it can't see the UI it builds. This screenshots
a running app and asks a VISION model (Qwen3.6, which has the vision capability) whether
it matches the spec. Used by `hermes-coder run` for kind=web projects.

Usage: ui_check.py <url> <spec_file> <out_png> [model] [ollama_host]
Exit 0 = UI=OK, non-zero = issues / couldn't capture.
"""
import sys, subprocess, base64, json, os, urllib.request

def screenshot(url, out):
    # snap chromium is confined: it can write only to NON-hidden files in the desktop
    # user's $HOME (the "home" interface excludes dotdirs like ~/.cache), and won't run
    # as root. So capture as that user, to a non-hidden temp, then copy to `out`.
    import pwd
    user = os.environ.get("HERMES_SHOT_USER") or os.environ.get("SUDO_USER")
    if not user and os.path.isdir("/home/elias"):
        user = "elias"
    try:
        home = pwd.getpwnam(user).pw_dir if user else os.path.expanduser("~")
    except KeyError:
        home, user = os.path.expanduser("~"), None
    tmp = os.path.join(home, "hermes-ui-shot.png")
    base = ["chromium", "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
            f"--screenshot={tmp}", "--window-size=1280,900",
            "--virtual-time-budget=4000", url]
    cmd = (["sudo", "-u", user] + base) if (os.geteuid() == 0 and user and user != "root") else base
    subprocess.run(cmd, capture_output=True, timeout=70)
    if os.path.exists(tmp) and os.path.getsize(tmp) > 0:
        subprocess.run(["cp", tmp, out], capture_output=True)
        try: os.remove(tmp)
        except OSError: pass
        return os.path.exists(out) and os.path.getsize(out) > 0
    return False

def vision_check(png, spec, model, host):
    b64 = base64.b64encode(open(png, "rb").read()).decode()
    prompt = ("You are validating a web UI screenshot against a spec.\n\nSPEC:\n" + spec +
              "\n\nLook at the screenshot. Does the UI plausibly implement the spec — the "
              "expected elements present, not a blank page, not an error/traceback page? "
              "Answer on ONE line: 'UI=OK' if it looks right, otherwise "
              "'UI=ISSUES: <short list of what's wrong/missing>'.")
    # think:false — qwen3.6 is a thinking model; reasoning chains make the vision call
    # time out. Disable it + cap output for a fast one-line verdict.
    body = json.dumps({"model": model, "stream": False, "think": False,
                       "options": {"num_predict": 150},
                       "messages": [{"role": "user", "content": prompt, "images": [b64]}]}).encode()
    req = urllib.request.Request(host + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        d = json.load(r)
    return d.get("message", {}).get("content", "").strip()

def main():
    url = sys.argv[1]; specfile = sys.argv[2]; out = sys.argv[3]
    model = sys.argv[4] if len(sys.argv) > 4 else "qwen3.6:35b"
    host = sys.argv[5] if len(sys.argv) > 5 else "http://127.0.0.1:11434"
    spec = open(specfile, encoding="utf-8", errors="ignore").read() if os.path.exists(specfile) else "(no spec)"
    if not screenshot(url, out):
        print("UI=ISSUES: could not capture a screenshot (app not serving HTML?)")
        return 1
    print(f"  screenshot saved: {out} ({os.path.getsize(out)} bytes)")
    try:
        verdict = vision_check(out, spec, model, host)
    except Exception as e:
        print(f"  vision call failed: {e}")
        return 2
    print("  vision verdict:", " ".join(verdict.split())[:300])
    return 0 if "UI=OK" in verdict else 1

if __name__ == "__main__":
    sys.exit(main())
