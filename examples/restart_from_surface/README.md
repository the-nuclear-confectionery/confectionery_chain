# Restart from a freeze-out surface

`BQSSampler → SMASH decays → Q-vectors`

The fastest turnaround loop: re-sample an existing CCAKE freeze-out surface with
different sampler / afterburner settings **without re-running hydro**. Persist a
surface from a hydro run with `hydrodynamics.parameters.keep_result: true` (writes
`freeze_out_<id>.dat`), then point this config at it.

**Key knobs:**
- Every upstream stage (`initial_conditions`, `overlay`, `preequilibrium`,
  `hydrodynamics`) is `none`.
- `particlization.parameters.input_file` — path to the freeze-out surface.
- `dimension` (2 vs 3) must match the surface; `use_muB/S/Q` should match whether
  the surface carries BSQ chemical potentials; `eos_column: false` for old
  surfaces without the column-44 EoS flag.

**Run:**
```sh
python wrapper/main.py 0 restart.db examples/restart_from_surface/config.yml
```
