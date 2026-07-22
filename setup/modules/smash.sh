#!/usr/bin/env bash
# SMASH afterburner (installed into the conda prefix; wrapper invokes `smash`).
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
require_conda

cmake_build "$WORKDIR/models/smash" \
  -DPythia_CONFIG_EXECUTABLE="$PREFIX/pythia8316/bin/pythia8-config" \
  -DCMAKE_INSTALL_PREFIX="$PREFIX"
cmake --build "$WORKDIR/models/smash/build" --target install
log "SMASH installed: $PREFIX/bin/smash"
