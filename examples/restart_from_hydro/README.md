# Restart from a hydro initial condition

`CCAKE → BQSSampler → SMASH decays → Q-vectors`

Skip IC / overlay / pre-equilibrium and run **hydro onward** from an existing
CCAKE-format initial condition. Use it to re-run hydro (and everything after) on
a saved IC — e.g. a `ccake_ic_<id>.dat` persisted from a previous TRENTo/AMPT run
with `initial_conditions.parameters.keep_result: true`.

**Key knobs:**
- `initial_conditions.type`, `overlay.type`, `preequilibrium.type` are all `none`.
- Because there is no upstream stage to infer the IC from, you **must** set both
  `hydrodynamics.initial_conditions.file` and `.type` (CCAKE errors otherwise).
- Match `global.tau_hydro`, the grid dimensionality, and
  `hydrodynamics.initial_conditions.dimension` to the IC file you provide.

**Run:**
```sh
python wrapper/main.py 0 restart.db examples/restart_from_hydro/config.yml
```
