#!/usr/bin/env bash
# CCAKE hydrodynamics. Ensures the Houston EoS tables are present first.
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
require_conda

src="$WORKDIR/models/CCAKE"
[[ -d "$src" ]] || die "models/CCAKE missing — run: git submodule update --init models/CCAKE"

# Apply local CCAKE source patches kept in setup/patches/ (so fixes ship without
# committing the CCAKE submodule). Uses `patch` rather than `git apply` so it
# also works where .git is absent (e.g. container builds). Idempotent: a reverse
# dry-run detects an already-applied patch and skips it.
for patch_file in "$WORKDIR"/setup/patches/ccake-*.patch; do
  [[ -e "$patch_file" ]] || continue
  pname="$(basename "$patch_file")"
  if patch -p1 -R --dry-run -f -d "$src" <"$patch_file" >/dev/null 2>&1; then
    log "CCAKE patch already applied: $pname"
  elif patch -p1 --dry-run -f -d "$src" <"$patch_file" >/dev/null 2>&1; then
    patch -p1 -d "$src" <"$patch_file" >/dev/null
    log "applied CCAKE patch: $pname"
  else
    warn "CCAKE patch does not apply cleanly, skipping: $pname"
  fi
done

eos_dir="$src/EoS/Houston"
mkdir -p "$eos_dir"
[[ -s "$eos_dir/thermo.dat" ]] || wget -O "$eos_dir/thermo.dat" 'https://zenodo.org/record/6829115/files/thermo.dat?download=1'
[[ -s "$eos_dir/thermo.h5"  ]] || wget -O "$eos_dir/thermo.h5"  'https://zenodo.org/record/6829115/files/thermo.h5?download=1'

cmake_build "$src"
log "CCAKE built: $src/build/ccake"
