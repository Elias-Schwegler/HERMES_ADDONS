#!/usr/bin/env bash
# Deploy the Hermes coder platform. Run as root:  sudo bash coder/install.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SHARE=/usr/local/share/hermes-coder

echo "[1] wrappers -> /usr/local/bin"
install -m 755 "$HERE/hermes-container" /usr/local/bin/hermes-container
install -m 755 "$HERE/hermes-coder"     /usr/local/bin/hermes-coder

echo "[2] shared assets -> $SHARE  (AGENTS.md, opencode config, gates, vision)"
install -d "$SHARE" "$SHARE/gates" "$SHARE/vision"
install -m 644 "$HERE/AGENTS.md"            "$SHARE/AGENTS.md"
install -m 644 "$HERE/opencode.coder.json"  "$SHARE/opencode.coder.json"
install -m 644 "$HERE/gates/check_no_stubs.py" "$SHARE/gates/check_no_stubs.py"
install -m 644 "$HERE/vision/ui_check.py"      "$SHARE/vision/ui_check.py"

echo "[3] bounded sudoers (hermesbot -> ONLY hermes-container + hermes-coder)"
install -m 440 "$HERE/hermes-coder.sudoers" /etc/sudoers.d/hermes-coder
visudo -cf /etc/sudoers.d/hermes-coder

echo "[4] coder model unit -> ornith-coder.service (raw llama-server, clean tool_calls)"
install -m 644 "$HERE/ornith-coder.service" /etc/systemd/system/ornith-coder.service
systemctl daemon-reload

echo "[5] deploy-list (gc keep-list)"
mkdir -p /etc/hermes-coder; touch /etc/hermes-coder/deployed.list

echo "[6] build the sandbox image"
docker build -t hermes-coder-sandbox:latest -f "$HERE/Dockerfile.sandbox" "$HERE" >/dev/null \
  && echo "    built hermes-coder-sandbox:latest"

cat <<'NOTE'

DONE. Coder platform installed.

One-time Hermes wiring (manual, host-specific):
  - add 'hermes-coder' to Hermes' command_allowlist in ~hermesbot/.hermes/config.yaml
  - install coder/hermes-skill-code.md as a Hermes skill and register /code

Lifecycle:
  - the model (ornith-coder.service) is started on demand by `hermes-coder new`
    and stopped when idle by `hermes-coder finish`.
  - UI vision check needs a desktop user with snap chromium; set $HERMES_SHOT_USER
    if it isn't the SUDO_USER.
NOTE
