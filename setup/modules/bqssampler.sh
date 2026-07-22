#!/usr/bin/env bash
# BQSSampler particlization. Reassembles the split grad_coeffs table first.
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
require_conda

src="$WORKDIR/models/BQSSampler"
[[ -d "$src" ]] || die "models/BQSSampler missing — run: git submodule update --init models/BQSSampler"

if [[ ! -s "$src/tables/grad_coeffs.dat" ]]; then
  cat "$src"/tables/grad_coeffs.dat.part_* > "$src/tables/grad_coeffs.dat"
fi

cmake_build "$src"
log "BQSSampler built: $src/build/particlizer"
