# Shared helpers for chain setup scripts. Source this; do not execute.
set -euo pipefail

# Repo root = parent of the setup/ directory this file lives in
CHAIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export WORKDIR="${WORKDIR:-$CHAIN_ROOT}"
export JOBS="${CHAIN_JOBS:-$(nproc 2>/dev/null || echo 8)}"

log()  { printf '\033[1;34m[chain]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[chain] WARNING:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[chain] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

require_conda() {
  [[ -n "${CONDA_PREFIX:-}" ]] || die "no active conda environment; activate the chain env first (see README)"
  export PREFIX="$CONDA_PREFIX"
  # Build-time locations expected by the modules (same values `setup/env.sh`
  # persists into the conda env itself).
  export CPATH="${PREFIX}/include"
  export CABANASRC="${PREFIX}/cabana"
  export KOKKOSSRC="${PREFIX}/kokkos"
  export EIGEN3_ROOT="${PREFIX}/eigen3"
  export PYTHIA8DIR="${PREFIX}/pythia8316"
  export PYTHIA8_ROOT_DIR="${PREFIX}/pythia8316"
  export HEPMC_DIR="${PREFIX}"
  export SMASH_DIR="${WORKDIR}/models/smash"
}

# Stamps mark completed external-dependency installs inside the conda prefix,
# so reruns of `chain install` skip them.
stamp_dir() { echo "$PREFIX/.chain_stamps"; }
has_stamp() { [[ -f "$(stamp_dir)/$1" ]]; }
put_stamp() { mkdir -p "$(stamp_dir)"; touch "$(stamp_dir)/$1"; }

# cmake_build <src_dir> [extra cmake args...]
# Configure+build in <src_dir>/build; wipes the build dir first when CLEAN=1.
cmake_build() {
  local src="$1"; shift
  [[ -d "$src" ]] || die "source dir not found: $src (run 'git submodule update --init' first?)"
  if [[ "${CLEAN:-0}" == "1" ]]; then
    log "removing $src/build"
    rm -rf "$src/build"
  fi
  mkdir -p "$src/build"
  cmake -S "$src" -B "$src/build" "$@"
  cmake --build "$src/build" -j "$JOBS"
}
