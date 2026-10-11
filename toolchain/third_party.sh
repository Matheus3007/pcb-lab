#!/usr/bin/env bash
# Fetch third-party data this repo uses but does not redistribute (see THIRD_PARTY.md).
# Every file is pinned (upstream commit or LCSC ID) and verified by SHA-256, so builds stay
# reproducible. Idempotent; called by setup.sh. Add new entries here instead of committing them.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

# --- CPL rotation hints: matthewlai/JLCKicadTools (GPL-3.0), pinned commit, our 3-line header on top
f="$root/lib/jlc_rotations.csv"
if [ ! -f "$f" ]; then
  curl -fsSL -o "$tmp/up.csv" \
    https://raw.githubusercontent.com/matthewlai/JLCKicadTools/50ab53794357e2217bf56cae1381be5ff23dbb37/jlc_kicad_tools/cpl_rotations_db.csv
  { echo "# Source: github.com/matthewlai/JLCKicadTools cpl_rotations_db.csv (last upstream change 2024-09-11), fetched 2026-10-11."
    echo "# HINTS ONLY: confirm every rotation in JLC's placement preview at gate 3, and fix entries here when wrong."
    echo "# Our own confirmed corrections go at the TOP (first match wins)."
    cat "$tmp/up.csv"; } > "$f"
fi

# --- 3D models from LCSC/EasyEDA via easyeda2kicad:  step LCSC_ID DEST
step() {
  local dest="$root/$2"
  [ -f "$dest" ] && return
  mkdir -p "$(dirname "$dest")"
  (cd "$tmp" && "$root/toolchain/.venv/bin/easyeda2kicad" --3d --lcsc_id "$1" --output "$tmp/$1" >"$tmp/log" 2>&1) || { cat "$tmp/log"; exit 1; }
  mv "$(find "$tmp" -path "*$1.3dshapes/*.step" | head -1)" "$dest"
}
step C165948 lib/3d/HRO_TYPE-C-31-M-12_C165948.step

# verify everything listed in the manifest
(cd "$root" && sha256sum -c --quiet toolchain/third_party.sha256) || { echo "third_party: checksum mismatch (see above)"; exit 1; }
echo "third-party data ready"
