#!/usr/bin/env bash
# Kokkos (OpenMP+Serial, no CUDA) into the conda prefix. Idempotent via stamp.
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
require_conda

KOKKOS_TAG=4.1.00

if has_stamp "kokkos-$KOKKOS_TAG"; then
  log "Kokkos $KOKKOS_TAG already installed — skipping"
  exit 0
fi

[[ -d "$KOKKOSSRC/.git" ]] || git clone https://github.com/kokkos/kokkos.git "$KOKKOSSRC"
git -C "$KOKKOSSRC" fetch --quiet origin || true
git -C "$KOKKOSSRC" checkout --quiet "$KOKKOS_TAG"

mkdir -p "$KOKKOSSRC/build"
cmake -S "$KOKKOSSRC" -B "$KOKKOSSRC/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DCMAKE_CXX_COMPILER=g++ \
  -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_CXX_EXTENSIONS=Off \
  -DKokkos_ENABLE_COMPILER_WARNINGS=ON \
  -DKokkos_ENABLE_CUDA=Off \
  -DKokkos_ENABLE_CUDA_LAMBDA=Off \
  -DKokkos_ENABLE_OPENMP=On \
  -DKokkos_ENABLE_SERIAL=On \
  -DKokkos_ENABLE_TESTS=Off \
  -DKokkos_ARCH_AMPERE80=Off
cmake --build "$KOKKOSSRC/build" -j "$JOBS" --target install

put_stamp "kokkos-$KOKKOS_TAG"
log "Kokkos installed"
