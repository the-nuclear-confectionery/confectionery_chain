#!/usr/bin/env bash
# Q-vector writer analysis module.
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
require_conda

cmake_build "$WORKDIR/models/qvector_writter"
log "qvector_writter built: $WORKDIR/models/qvector_writter/build/qvector_writter.exe"
