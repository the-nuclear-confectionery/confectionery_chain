#!/usr/bin/env bash
# AMPT (Fortran). Built in-tree with gfortran via its own Makefile.
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
require_conda

src="$WORKDIR/models/AMPT"
[[ -f "$src/Makefile" ]] || die "models/AMPT missing — run: git submodule update --init models/AMPT"

if [[ "${CLEAN:-0}" == "1" ]]; then
  make -C "$src" clean || true
fi
make -C "$src" -j"$JOBS" FC=gfortran
log "AMPT built: $src/ampt"
