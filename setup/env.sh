#!/usr/bin/env bash
# Persist chain environment variables into the active conda env so they are
# set automatically on every `conda activate`. Rerunnable.
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
require_conda

log "persisting environment variables into conda env at $PREFIX"
conda env config vars set \
  PREFIX="$PREFIX" \
  WORKDIR="$WORKDIR" \
  CPATH="$PREFIX/include" \
  CABANASRC="$CABANASRC" \
  KOKKOSSRC="$KOKKOSSRC" \
  EIGEN3_ROOT="$EIGEN3_ROOT" \
  PYTHIA8DIR="$PYTHIA8DIR" \
  PYTHIA8_ROOT_DIR="$PYTHIA8_ROOT_DIR" \
  HEPMC_DIR="$HEPMC_DIR" \
  SMASH_DIR="$SMASH_DIR"

log "done — deactivate and reactivate the env for the variables to take effect"
