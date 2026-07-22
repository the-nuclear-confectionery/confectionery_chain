#!/usr/bin/env bash
# Q-vector analysis (post-processing of qvector_writter output).
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
require_conda

cmake_build "$WORKDIR/analysis/qvector_analysis"
log "qvector_analysis built in $WORKDIR/analysis/qvector_analysis/build"
