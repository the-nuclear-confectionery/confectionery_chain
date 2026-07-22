#!/usr/bin/env bash
# decays afterburner.
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
require_conda

cmake_build "$WORKDIR/models/decays" -DCMAKE_POLICY_VERSION_MINIMUM=3.5
log "decays built: $WORKDIR/models/decays/build/decays"
