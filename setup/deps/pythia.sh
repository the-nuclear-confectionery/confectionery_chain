#!/usr/bin/env bash
# PYTHIA 8.316 into the conda prefix. Idempotent via stamp + existing install.
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
require_conda

PYTHIA_VER=8316

if has_stamp "pythia-$PYTHIA_VER" && [[ -x "$PREFIX/pythia$PYTHIA_VER/bin/pythia8-config" ]]; then
  log "PYTHIA $PYTHIA_VER already installed — skipping"
  exit 0
fi

cd "$PREFIX"
if [[ ! -d "pythia$PYTHIA_VER" ]]; then
  [[ -f "pythia$PYTHIA_VER.tgz" ]] || wget "https://pythia.org/download/pythia83/pythia$PYTHIA_VER.tgz"
  tar xf "pythia$PYTHIA_VER.tgz" && rm -f "pythia$PYTHIA_VER.tgz"
fi
cd "pythia$PYTHIA_VER"
./configure --prefix="$PREFIX" --with-hepmc3="$PREFIX" \
  --cxx-common='-std=c++17 -march=native -O3 -fPIC -pthread'
make -j"$JOBS" install

put_stamp "pythia-$PYTHIA_VER"
log "PYTHIA installed"
