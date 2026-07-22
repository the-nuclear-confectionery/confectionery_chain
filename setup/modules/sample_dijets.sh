#!/usr/bin/env bash
# sample_dijets: dijet sampler for jet initial conditions (needs PYTHIA8).
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
require_conda

src="$WORKDIR/utils/sample_dijets"
[[ -f "$src/sample_dijets.cpp" ]] || die "utils/sample_dijets sources missing"
[[ -x "$PYTHIA8DIR/bin/pythia8-config" ]] || die "PYTHIA8 not found at $PYTHIA8DIR — run ./chain install first"

if [[ "${CLEAN:-0}" == "1" ]]; then
  make -C "$src" clean || true
fi
make -C "$src" PYTHIA8="$PYTHIA8DIR"
log "sample_dijets built: $src/sample_dijets"
