#!/usr/bin/env bash
# Analytical Cooper-Frye particlization (in-tree make).
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
require_conda

src="$WORKDIR/models/analytical_cooperfrye"
if [[ "${CLEAN:-0}" == "1" ]]; then
  make -C "$src" clean || true
fi
make -C "$src" -j"$JOBS"
log "analytical_cooperfrye built: $src/fo"
