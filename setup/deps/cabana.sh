#!/usr/bin/env bash
# Cabana (on top of Kokkos) into the conda prefix. Idempotent via stamp.
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
require_conda

CABANA_SHA=2b642f8dbba760e2008f8b81a4196e6adf100f42

if has_stamp "cabana-$CABANA_SHA"; then
  log "Cabana $CABANA_SHA already installed — skipping"
  exit 0
fi

[[ -d "$CABANASRC/.git" ]] || git clone https://github.com/ECP-copa/Cabana.git "$CABANASRC"
git -C "$CABANASRC" fetch --quiet origin || true
git -C "$CABANASRC" checkout --quiet "$CABANA_SHA"

mkdir -p "$CABANASRC/build"
cmake -S "$CABANASRC" -B "$CABANASRC/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_PREFIX_PATH="$CABANASRC" \
  -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DCMAKE_CXX_COMPILER=g++ \
  -DCabana_REQUIRE_CUDA=OFF \
  -DCabana_ENABLE_TESTING=OFF \
  -DCabana_ENABLE_EXAMPLES=OFF
cmake --build "$CABANASRC/build" -j "$JOBS" --target install

put_stamp "cabana-$CABANA_SHA"
log "Cabana installed"
