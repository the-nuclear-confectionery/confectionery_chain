#!/usr/bin/env bash
# AMPTGenesis overlay (smears AMPT partons onto a hydro grid).
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
require_conda

cmake_build "$WORKDIR/models/AMPTGenesis"
log "AMPTGenesis built: $WORKDIR/models/AMPTGenesis/build/AMPT-Genesis.exe"
