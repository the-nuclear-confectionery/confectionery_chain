#!/usr/bin/env bash
# TRENTo initial conditions.
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
require_conda

cmake_build "$WORKDIR/models/trento" \
  -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build "$WORKDIR/models/trento/build" --target install
log "trento built: $WORKDIR/models/trento/build/src/trento"
