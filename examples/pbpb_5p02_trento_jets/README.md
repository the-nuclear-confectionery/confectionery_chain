# Pb+Pb @ 5.02 TeV — dijets sampled from the TRENTo binary collisions

`TRENTo (entropy + ncoll) → CCAKE (2+1D + BBMG jets) → BQSSampler → SMASH decays → Q-vectors`

Demonstrates jet sampling driven by the **TRENTo** collision geometry. The
`jets_sampling` stage runs `utils/sample_dijets` on this event's TRENTo
binary-collision list (`ncoll_list0.dat`), samples back-to-back PYTHIA dijets at
those vertices, free-streams them to `tau_hydro`, and points CCAKE's
`hydro.jets` at them. `hydro.jets.type: BBMG` evolves the jets and
`hydro.source.type: jet` feeds their energy loss back into the fluid.

**Physics case:** LHC Pb+Pb with hard dijets embedded consistently in the
soft background that sourced the hydro.

**Requirements / key knobs:**
- `initial_conditions.parameters.ncoll: true` — **required**; makes TRENTo write
  the `ncoll_list0.dat` binary-collision vertices.
- `jets_sampling.vertex_source: trento` — sample vertices from those collisions
  (vs `binary`/`minijet`, which need an AMPT IC).
- `jets_sampling.{n_dijets, pt_min, pt_max}` — how many dijets and the PYTHIA
  pT-hat window (must stay below √s/2 = 2510 GeV).
- `hydro.jets.type: BBMG` + `hydro.source.type: jet` — evolve the jets and couple
  their energy loss into the fluid.
- `output.jet_evolution: true` — dump per-step jet state.

**Run:**
```sh
python wrapper/main.py 0 pbpb_5p02.db examples/pbpb_5p02_trento_jets/config.yml
```
