#!/usr/bin/env bash
# iS3D particlization.
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
require_conda

cmake_build "$WORKDIR/models/iS3D"
cmake --build "$WORKDIR/models/iS3D/build" --target install
log "iS3D built: $WORKDIR/models/iS3D/iS3D"
