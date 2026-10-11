# source toolchain/env.sh: puts the pinned tools on PATH for this shell.
_root="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
export PATH="$_root/toolchain/bin:$_root/toolchain/.venv/bin:$HOME/.local/bin:$PATH"
export PCBLAB_ROOT="$_root"
unset _root
