#!/usr/bin/env bash
# CCAKE hydrodynamics. Ensures the Houston EoS tables are present first.
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
require_conda

src="$WORKDIR/models/CCAKE"
[[ -d "$src" ]] || die "models/CCAKE missing — run: git submodule update --init models/CCAKE"

eos_dir="$src/EoS/Houston"
mkdir -p "$eos_dir"
[[ -s "$eos_dir/thermo.dat" ]] || wget -O "$eos_dir/thermo.dat" 'https://zenodo.org/record/6829115/files/thermo.dat?download=1'
[[ -s "$eos_dir/thermo.h5"  ]] || wget -O "$eos_dir/thermo.h5"  'https://zenodo.org/record/6829115/files/thermo.h5?download=1'

cmake_build "$src"
log "CCAKE built: $src/build/ccake"
