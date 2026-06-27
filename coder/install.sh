#!/usr/bin/env bash
# Deploy the Hermes coder platform. Run as root:  sudo bash coder/install.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "[1] hermes-container wrapper -> /usr/local/bin"
install -m 755 "$HERE/hermes-container" /usr/local/bin/hermes-container

echo "[2] bounded sudoers (hermesbot -> ONLY hermes-container, no direct docker)"
install -m 440 "$HERE/hermes-coder.sudoers" /etc/sudoers.d/hermes-coder
visudo -cf /etc/sudoers.d/hermes-coder

echo "[3] deploy-list (gc keep-list for deployed containers)"
mkdir -p /etc/hermes-coder; touch /etc/hermes-coder/deployed.list

echo "[4] build the sandbox image"
docker build -t hermes-coder-sandbox:latest -f "$HERE/Dockerfile.sandbox" "$HERE" >/dev/null && echo "    built hermes-coder-sandbox:latest"

echo "DONE — hermesbot can now manage ONLY hermes-coder.* containers via the wrapper."
