#!/usr/bin/env bash
# Deploy the hermes-stack custom layer to the system. Run as root: sudo bash deploy/install.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"

echo "[1] hermes-container wrapper -> /usr/local/bin"
install -m 755 "$HERE/bin/hermes-container" /usr/local/bin/hermes-container

echo "[2] sudoers (hermesbot -> only hermes-container)"
install -m 440 "$HERE/deploy/hermes-coder.sudoers" /etc/sudoers.d/hermes-coder
visudo -cf /etc/sudoers.d/hermes-coder

echo "[3] deploy-list dir"
mkdir -p /etc/hermes-coder; touch /etc/hermes-coder/deployed.list

echo "DONE"
