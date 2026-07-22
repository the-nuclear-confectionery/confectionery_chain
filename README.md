# test_chain

Orchestrates a heavy-ion collision simulation chain — initial condition,
overlay, preequilibrium, hydrodynamics, particlization, afterburner, and
analysis — as a sequence of independently swappable modules driven by a
single YAML configuration per event.

```
initial_conditions -> overlay -> preequilibrium -> hydrodynamics
   -> particlization -> afterburner -> analysis
```

Each arrow is a file handoff on disk; any stage can be set to `none` to break
the chain there (e.g. to restart from an existing freeze-out surface). See
[examples/](examples/) for complete, validated configurations.

## Modules

| Module | Role | Repo | Branch |
|---|---|---|---|
| [AMPT](models/AMPT) | initial condition (heavy-ion transport) | the-nuclear-confectionery/AMPT | main |
| [trento](models/trento) | initial condition (entropy deposition) | the-nuclear-confectionery/trento | cpp |
| [AMPTGenesis](models/AMPTGenesis) | overlay (AMPT parton smearing -> hydro grid) | USPHydro/AMPTGenesis | cartesian |
| [ICCING](models/ICCING) | overlay (initial-state charge fluctuations) | the-nuclear-confectionery/ICCING | cpp_fix |
| [freestream](models/freestream) | preequilibrium (free streaming) | Duke-QCD/freestream | (vendored, unpinned) |
| [CCAKE](models/CCAKE) | hydrodynamics (viscous SPH, BSQ charges, jets) | the-nuclear-confectionery/CCAKE | main |
| [iS3D](models/iS3D) | particlization (Cooper-Frye sampling) | the-nuclear-confectionery/iS3D | master |
| [BQSSampler](models/BQSSampler) | particlization (BSQ Cooper-Frye sampling) | the-nuclear-confectionery/BQSSampler | main |
| [analytical_cooperfrye](models/analytical_cooperfrye) | particlization (analytic spectra) | in-tree | — |
| [smash](models/smash) | afterburner (hadronic transport / decays) | the-nuclear-confectionery/smash | main |
| [decays](models/decays) | afterburner (resonance decays only) | the-nuclear-confectionery/decays | nuc |
| [qvector_writter](models/qvector_writter) | analysis (flow harmonics) | the-nuclear-confectionery/qvector_writter | main |
| [qvector_analysis](analysis/qvector_analysis) | analysis (Q-vector post-processing) | the-nuclear-confectionery/qvector_analysis | main |
| [sample_dijets](utils/sample_dijets) | jet sampling for CCAKE initial conditions | in-tree | — |

All submodules are pinned to a specific commit, recorded in `test_chain`'s own
git history — `./chain status` shows pinned vs. checked-out vs. remote-tip
commits for each. Local modifications inside a submodule are never touched by
`./chain`; it warns and skips instead of overwriting your work.

## Quickstart

```sh
git clone git@github.com:the-nuclear-confectionery/test_chain.git
cd test_chain

conda env create -f environment.yaml   # creates env "ctop" (or activate your own)
conda activate ctop

./chain install                        # submodules + deps + all modules + tables
conda deactivate && conda activate ctop  # pick up env vars ./chain install set

./chain doctor                         # verify the install
```

`./chain install` populates any missing submodules itself, so a plain `git
clone` (no `--recurse-submodules`) is enough. The two steps that *can't* be
folded in: the top-level `git clone` (this script lives inside the repo), and
creating/activating the conda env (a script can't activate an env in your
interactive shell — hence the reactivation line above).

Run one event:

```sh
python wrapper/main.py 0 my_run.db examples/auau_19p6_ampt_full/config.yml
```

- Results land in `<config.global.output>/event_0/`.
- Run metadata (stage types, seeds, centrality) goes in `my_run.db` (SQLite,
  created if missing).
- A `provenance.yml` is written into each event's output directory recording
  the exact commit of test_chain and every submodule, plus the fully-resolved
  config — so any result stays traceable after later `./chain update`s.

For many events on SLURM, see `scripts/` and `submit_chain_ampt.sh`.

## The `./chain` CLI

Replaces the old monolithic `install` script (kept as a thin wrapper for
compatibility) with idempotent, individually rerunnable pieces:

```sh
./chain install              # everything: deps, all modules, tables
./chain rebuild ccake         # wipe and rebuild one module
./chain update ccake --latest # fetch a module's branch tip (skips dirty ones)
./chain update --all          # sync every submodule to test_chain's pinned commit
./chain status                # pinned vs. checked-out vs. dirty, per module
./chain status --remote       # also fetch and show each branch's remote tip
./chain doctor                # environment, dependency, and build sanity checks
./chain validate t0           # schema + unit tests (seconds)
./chain validate t1           # tiny-grid smoke chains (minutes, needs builds)
./chain validate t2           # physics validation (see below; long-running)
./chain modules                # list known module names
```

`update` never touches a submodule with local modifications — it warns and
skips so in-progress work in a submodule is never silently discarded.

Build logs go to `setup/logs/<name>.log`; external dependencies (HepMC3,
PYTHIA8, Kokkos, Cabana) are installed once into `$CONDA_PREFIX` and skipped
on subsequent `./chain install` runs via stamp files.

## Validation

Three tiers, all runnable via `./chain validate <tier>` (or `pytest
tests/<tier>` directly):

- **T0** — schema-validate every example and test config, plus golden-file
  unit tests of the pure format converters (dijets CSV -> CCAKE jets file,
  AMPT input-card writer, ...). Seconds, no builds required. Runs in CI on
  every push/PR (`.github/workflows/t0.yml`).
- **T1** — tiny-grid smoke chains (`tests/t1/configs/`) exercising the full
  AMPT, jets, and TRENTo+ICCING pipelines end to end, asserting each stage's
  declared outputs exist. Minutes; needs `./chain install`.
- **T2** — physics validation: CCAKE's viscous evolution checked against the
  semi-analytic Gubser solution (`tests/t2/gubser/`), conserved-charge and
  entropy monitoring on a real AMPT event (`tests/t2/test_conservation.py`),
  and fixed-seed observable regression against stored references
  (`tests/t2/references/`, provenance-stamped; regenerate deliberately with
  `tests/t2/references/regenerate_references.py` after an intentional physics
  change). Long-running — submit via `tests/run_t2.sbatch` on SLURM.

## Jet-embedded initial conditions

To sample dijets from an AMPT event's geometry and evolve them in CCAKE, add
to a chain config (requires `initial_conditions.type: ampt`):

```yaml
input:
  hydrodynamics:
    jets_sampling:
      enabled: true
      n_dijets: 1
      pt_min: 100.0
      pt_max: 200.0
    hydro:
      jets:
        type: full
```

See [utils/sample_dijets/README.md](utils/sample_dijets/README.md) for the
physics and file formats involved, and
`tests/t1/configs/jets_tiny.yml` for a complete working example.

## Repository layout

```
chain                  the CLI described above
setup/                  idempotent install/build scripts (deps, modules, tables)
wrapper/                the Python orchestrator (main.py + per-module stages)
  stages/               abstract per-stage interfaces
  specializations/       one implementation per module
  utils/                 schema validation, db, format converters, provenance
configs/all_options/    per-module reference configs: every flag, from the schema
examples/               curated, validated end-to-end chain configurations (runs)
tests/                  T0/T1/T2 validation suite
utils/sample_dijets/    dijet sampler for jet-embedded initial conditions
models/, analysis/      git submodules (see the module table above)
scripts/                SLURM batch helpers
```

## Troubleshooting

- **`./chain doctor` reports a missing dependency or module** — rerun
  `./chain install` (idempotent) or `./chain rebuild <module>` for a single
  one; check `setup/logs/<name>.log` for the build error.
- **A submodule looks out of date** — `./chain status` shows pinned vs.
  checked-out vs. (with `--remote`) the branch tip. `./chain update <module>`
  syncs to the pinned commit; add `--latest` to move to the tip instead (then
  `git add`/`commit` the new pin).
- **A submodule shows `dirty`** — `./chain` will never touch it; resolve the
  local changes yourself (commit, stash, or discard) before updating.
