#!/usr/bin/env bash
# Idempotent toolchain install for WSL2 (no sudo needed). Run from anywhere.
# Prereq: KiCad 10 installed on Windows at C:\Program Files\KiCad\10.0.
set -euo pipefail
cd "$(dirname "$0")"; source ./versions.env
KBIN="/mnt/c/Program Files/KiCad/10.0/bin"
[ -x "$KBIN/kicad-cli.exe" ] || { echo "KiCad 10 not found at $KBIN"; exit 1; }
command -v uv >/dev/null || [ -x ~/.local/bin/uv ] || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
mkdir -p ~/.local/opt
if ! ls -d ~/.local/opt/jdk-${JAVA_VERSION}* >/dev/null 2>&1; then
  curl -sL "https://api.adoptium.net/v3/binary/latest/${JAVA_VERSION}/ga/linux/x64/jre/hotspot/normal/eclipse" | tar xz -C ~/.local/opt
fi
jar=~/.local/opt/freerouting/freerouting-${FREEROUTING_VERSION}.jar
[ -f "$jar" ] || { mkdir -p ~/.local/opt/freerouting; curl -sL -o "$jar" \
  "https://github.com/freerouting/freerouting/releases/download/v${FREEROUTING_VERSION}/freerouting-${FREEROUTING_VERSION}.jar"; }
[ -d .venv ] || uv venv -q --python "$PYTHON_VERSION" .venv
VIRTUAL_ENV="$PWD/.venv" uv pip install -q -r requirements.txt
"$KBIN/python.exe" -m pip install -q --disable-pip-version-check --upgrade \
  --target "$(wslpath -w "$PWD/.kipy-site")" -r "$(wslpath -w "$PWD/requirements-kicad.txt")"
rm -rf .kipy-site/numpy* .kipy-site/bin   # use KiCad's own numpy
chmod +x bin/*
./third_party.sh
echo "toolchain ready: source toolchain/env.sh"
