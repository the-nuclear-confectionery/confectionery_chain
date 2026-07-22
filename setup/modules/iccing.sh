#!/usr/bin/env bash
# ICCING overlay (in-tree make).
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
require_conda

src="$WORKDIR/models/ICCING"
[[ -d "$src" ]] || die "models/ICCING missing — run: git submodule update --init models/ICCING"
if [[ "${CLEAN:-0}" == "1" ]]; then
  make -C "$src" clean || true
fi
make -C "$src" -j"$JOBS"
log "ICCING built: $src/iccing"
