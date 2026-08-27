# confectionery_chain — CCAKE 2.0 paper reproduce set

Branch `paper-repro`, based on superproject `ab9317e` (the wrapper state as of the
2026-06-30 convergence run). Submodule pins updated to the commits that ACTUALLY
produced the paper's grid-convergence campaign (Figs 16–30), recovered from the
run-output timestamps + each repo's reflog (CCAKE stamps no git hash; taiga
run-time provenance.yml was unavailable).

| submodule            | paper commit | date       | note                              |
|----------------------|--------------|------------|-----------------------------------|
| models/CCAKE         | 0a37d5ac     | 2026-07-06 | run-day tree was 009a1e5a + UNCOMMITTED eos_interpolator; 0a37d5ac is the committed form of that same code, builds clean, physics identical on the online-inverter path (see below) |
| models/AMPTGenesis   | dc72ff8      | 2025-09-18 | bumped from 3f64692               |
| models/BQSSampler    | a335712      | 2026-05-28 | bumped from 460ef68               |
| models/qvector_writter | 0fe395c    | 2026-04-23 | unchanged (already matched)       |
| models/smash         | 7f30407a3    | 2026-02-24 | unchanged                         |
| analysis/qvector_analysis | ed0ed4c | 2025-10-24 | unchanged                         |
| models/decays        | 68b590d      | 2026-03-25 | unchanged                         |

Caveats:
- Recovers COMMITTED state as of 2026-06-30. Uncommitted edits present that day are
  not captured; the only exact record is the taiga provenance.yml/config.yml.
- Applies to the CONVERGENCE campaign. Coordinate figures (4–6) were re-run Aug 2026
  with CCAKE 3eb3ee4c; date other figure groups from their own outputs before quoting.
- trento / iS3D / ICCING / freestream left at ab9317e's pins (not used by the AMPT
  convergence chain).

## Why models/CCAKE is pinned to 0a37d5ac (not the run-day 009a1e5a)
Verified 2026-08-20 by reproducing run 200GeV/dxx0p3_dxeta0p1_h0p3. Commit `009a1e5a` (HEAD on
the 2026-06-30 run day) does NOT compile as-committed: `src/sph_workstation.cpp` calls an EoS API
(`efreeze_at_T`, `invert_e_to_s_host`, `query_thermo_host`) whose declaration+implementation were
only committed two commits later in `0a37d5ac` (2026-07-06). So the paper binary was built from a
working tree that already had that eos_interpolator code UNCOMMITTED. `0a37d5ac` is the committed
form of exactly that code — the nearest buildable commit.

Physics is unchanged between 009a1e5a and 0a37d5ac: NO evolution/EoS-online file differs
(sph_workstation.cpp, eom_default.cpp, system_state.cpp, eos.cpp/.h are byte-identical). The only
source added is the OFFLINE flat-table inverter (eos_interpolator.{h,cpp}, +546 lines), which is
guarded by `!online_inverter_enabled` and never runs on the online-inverter path the convergence
campaign uses — compiled but dead-at-runtime.

### BUILD-FLAG NOTE (verified 2026-08-20 by cold-clone build)
0a37d5ac's CMakeLists adds `-O3 -march=${CCAKE_ARCH} -mtune=${CCAKE_ARCH} -funroll-loops`, default
`CCAKE_ARCH=native`.
- ON DELTA: just build with the DEFAULT (`native` -> znver3). Cold clone builds+links+runs unaided
  in ~2 min. This is the "just works" path and matches the CPU the paper ran on.
- DO NOT pass `-DCCAKE_ARCH=x86-64-v3` (or any ISA-level name): the CMakeLists feeds CCAKE_ARCH into
  BOTH -march and -mtune, and gcc 13.3.0 REJECTS `-mtune=x86-64-v3` (mtune wants CPU names). Only a
  real CPU name (e.g. `znver3`, `skylake`) is valid for CCAKE_ARCH as written.
- FOR A PORTABLE binary (non-Zen3 host): one-line CMakeLists fix — decouple mtune, e.g.
  `-march=${CCAKE_ARCH} -mtune=generic`, then `-DCCAKE_ARCH=x86-64-v3` works.
FIDELITY nuance: the run-day 009a1e5a CMakeLists had NO -march block (plain Release -O3); 0a37d5ac's
default adds -march=native (host FMA). Same physics/algorithm (no evolution/EoS-online file changed);
any difference is numerical-noise level. `-ffast-math`/`-Ofast` are deliberately avoided upstream
(strict IEEE for the SPH root-finder / EoS inversion / causality).

## Config faithfulness (required to reproduce the numbers)
The CCAKE base is the paper's `input_ampt3.yaml` + generate_convergence.py overrides. Bulk is
**mode `cs2_dependent`, A=1.67552, p=2.0** (NOT zeta/s=0). Plus: charges OFF, shear eta/s=0.08,
t0=0.4, dim=3, h_T=h_eta=0.3, online inverter, EoS table /u/kpala/git_repos/paper/test_chain/tables.

## Reproduction result (2026-08-20, this pin set)
200 GeV coarse run dxx0p3_dxeta0p1_h0p3, charged pid0: M=111.5 vs paper 113.4 (-1.7%),
v2=0.0928 vs 0.0932 (-0.4%), v3=0.0240 vs 0.0233 (+2.8%), <pT>=0.676 vs 0.677. FAITHFUL
(within N_s=10k single-event sampling noise). v4 +36% = high-harmonic EP noise floor (abs 0.002).

## Shipped installer VERIFIED end-to-end (2026-08-20)
`conda env create -f environment.yaml && conda activate ctop && ./install` builds **15/16
components from a 100% conda-forge env** (~23 min, ~10 GB) — the ENTIRE critical pipeline
CCAKE→BQSSampler→SMASH→qvector plus HepMC3/Pythia8.316/Kokkos/Cabana/AMPT/AMPTGenesis/trento/
ICCING/decays. Three fixes were required and are now applied to this branch:
  1. environment.yaml `gsl=2.7.1`→`gsl=2.7` (2.7.1 only on the `defaults` channel, not conda-forge)
  2. install Pythia URL `/download/`→`/releases/` (old path 404s; also unblocks SMASH + qvector, which need Pythia 8.316)
  3. install iS3D `cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5` (declares cmake_min 2.8, rejected by cmake>=4)
Only **iS3D** does not build — an ALTERNATE sampler, OFF the critical path (a gcc-13 source bug,
`surface_file` undeclared, needs a 1-line code fix). Reviewer notes: run through a Bazel-clean shell
(Delta login exports Cray CC=cc/CXX=CC + gcc-toolset — a normal machine has none); if `conda activate`
doesn't switch envs, use the env directly; `install` line ~114 `cp -r EoS build` is cosmetic (CCAKE
builds regardless). Env solved with micromamba; classic anaconda solver was unusable here.

## Build / reproduce (clean clone) — VERIFIED to build+run unaided on Delta
```
git clone -b paper-repro --recursive <this-repo>   # all 11 submodule pins are pushed/fetchable
# CCAKE (paper hydro):  DELTA default arch just works
cd models/CCAKE && ./bootstrap.sh                  # deps: GSL, Kokkos/Cabana, HDF5, yaml-cpp
cmake -S . -B build \
  -DCMAKE_C_COMPILER=$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-gcc \
  -DCMAKE_CXX_COMPILER=$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-g++   # avoid Cray cc/CC
cmake --build build -j            # ~2 min -> build/ccake ; do NOT set CCAKE_ARCH=x86-64-v3 (see note)
# then AMPTGenesis (IC, build under an env with ROOT), BQSSampler+SMASH+qvector per each README.
```
Fresh conda env gotcha (Delta): `conda create --clone ctop10` does NOT copy GSL/ROOT (installed into
ctop10 outside conda's package DB). Provision from scratch with `conda install -c conda-forge gsl`
(+ Kokkos/Cabana/HDF5/yaml-cpp); CCAKE needs GSL, AMPTGenesis needs ROOT.
