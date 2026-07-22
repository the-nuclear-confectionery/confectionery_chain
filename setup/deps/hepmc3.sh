#!/usr/bin/env bash
# HepMC3 (with ROOT IO) into the conda prefix. Idempotent via stamp.
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
require_conda

HEPMC3_SHA=7c7f4e5b1ffa5702787ca6c40ccc26f356bedb75

if has_stamp "hepmc3-$HEPMC3_SHA"; then
  log "HepMC3 $HEPMC3_SHA already installed — skipping"
  exit 0
fi

cd "$PREFIX"
[[ -d HepMC3/.git ]] || git clone https://gitlab.cern.ch/hepmc/HepMC3.git
git -C HepMC3 fetch --quiet origin || true
git -C HepMC3 checkout --quiet "$HEPMC3_SHA"

mkdir -p hepmc3-build
cmake -S HepMC3 -B hepmc3-build \
  -DHEPMC3_ENABLE_ROOTIO=ON \
  -DROOT_DIR="${ROOTSYS:-$PREFIX}" \
  -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build hepmc3-build -j "$JOBS" --target install

put_stamp "hepmc3-$HEPMC3_SHA"
log "HepMC3 installed"
