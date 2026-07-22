#!/usr/bin/env bash
# Assemble the tables/ directory the wrapper rsyncs into every event tmp dir.
# Sources: CCAKE EoS (downloaded by setup/modules/ccake.sh), ICCING inputs,
# iS3D tables, BQSSampler tables. Rerunnable.
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

cd "$WORKDIR"
mkdir -p tables tables/ICCING tables/iS3D tables/BQSSampler tables/analytical_cooperfrye

# CCAKE EoS (Houston lattice tables)
if [[ ! -s tables/thermo.h5 ]]; then
  [[ -s models/CCAKE/EoS/Houston/thermo.h5 ]] || die "EoS tables missing — run: ./chain rebuild ccake (downloads them)"
  cp -f models/CCAKE/EoS/Houston/thermo.dat models/CCAKE/EoS/Houston/thermo.h5 tables/
fi

# ICCING inputs
cp -rf models/ICCING/Input/*.dat        tables/ICCING/ 2>/dev/null || true
cp -rf models/ICCING/Input/*.txt        tables/ICCING/ 2>/dev/null || true
cp -rf models/ICCING/Greens_Function/*.txt tables/ICCING/ 2>/dev/null || true

# iS3D tables
cp -rf models/iS3D/tables              tables/iS3D/
cp -rf models/iS3D/PDG                 tables/iS3D/
cp -rf models/iS3D/deltaf_coefficients tables/iS3D/

# BQSSampler tables (grad_coeffs.dat is assembled by setup/modules/bqssampler.sh)
cp -rf models/BQSSampler/tables/*.dat  tables/BQSSampler/

log "tables/ assembled"
