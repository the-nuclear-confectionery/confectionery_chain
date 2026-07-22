# Examples

Curated, validated **chain** configurations — realistic, runnable end-to-end
runs. Every config here is checked against the wrapper schema by the T0
validation suite (`./chain validate t0`); the core chains also have tiny-grid
twins in `tests/t1/` exercised by the smoke tests.

> Looking for **every flag a module accepts**? That is a different thing — see
> [`../configs/all_options/`](../configs/all_options/), which has one exhaustive
> reference config per module (all of TRENTo, all of AMPT, all of CCAKE, …). The
> examples here are curated runs, not flag catalogs.

**Full chains**

| Example | Chain | Physics case |
|---|---|---|
| [auau_19p6_ampt_full](auau_19p6_ampt_full/) | AMPT → AMPTGenesis → CCAKE 3+1D → BQSSampler → SMASH → Q-vectors | BES Au+Au, baryon-rich (3+1)D |
| [auau_19p6_ampt_source](auau_19p6_ampt_source/) | AMPT → AMPTGenesis → CCAKE 3+1D **+ AMPT source** → BQSSampler → SMASH → Q-vectors | BES Au+Au, late partons fed in as a continuous source term |
| [pbpb_5p02_trento_iccing](pbpb_5p02_trento_iccing/) | TRENTo → ICCING → CCAKE 2+1D → BQSSampler → SMASH → Q-vectors | LHC Pb+Pb with initial-state BSQ charge fluctuations |
| [pbpb_5p02_trento_ccake](pbpb_5p02_trento_ccake/) | TRENTo → CCAKE 2+1D → BQSSampler → SMASH → Q-vectors | LHC Pb+Pb, charge-less, entropy input (simplest path) |
| [pbpb_5p02_trento_jets](pbpb_5p02_trento_jets/) | TRENTo → CCAKE 2+1D **+ sampled dijets** → BQSSampler → SMASH → Q-vectors | LHC Pb+Pb, dijets sampled from the TRENTo binary collisions |

**Partial chains (restart)**

| Example | Chain | Restart point |
|---|---|---|
| [restart_from_hydro](restart_from_hydro/) | CCAKE → BQSSampler → SMASH → Q-vectors | an existing CCAKE-format IC file |
| [restart_from_surface](restart_from_surface/) | BQSSampler → SMASH → Q-vectors | an existing freeze-out surface (`freeze_out.dat`) |

A `TRENTo → free-streaming → CCAKE → …` chain is intentionally not shipped yet —
the free-streaming stage has a known bug (see
[../docs/KNOWN_ISSUES.md](../docs/KNOWN_ISSUES.md)).

All particlization uses **BQSSampler** (iS3D is legacy). All EoS notes: the
shipped `tables/` are the Houston BSQ tables (muB~0, LHC) and need
`normalize_by_T: true` + `restrict_mu_T_ratios: true`; baryon-rich BES/AMPT
runs need a separate baryon-rich holographic EoS (+ gap table), which you must
supply — see the auau example.

## How to use

1. Copy the example's `config.yml` somewhere (or edit in place).
2. Replace the `<REPLACE:...>` placeholders — `output` (results), `tmp`
   (scratch), `basedir` (this repository's root). Everything else has
   physically motivated defaults documented inline and in
   `wrapper/utils/schema.yml`.
3. Run one event:

   ```sh
   python wrapper/main.py <event_id> <database.db> <config.yml>
   ```

4. For many events on SLURM, see `scripts/` and `submit_chain_ampt.sh`.

## Partial chains

Any stage can be set to `type: none` (or omitted); stages read their inputs
from the previous stage's per-event output directory, or from explicit
`input_file`/`paths` overrides. This is how you restart from an existing
freeze-out surface — set `initial_conditions`/`overlay`/`hydrodynamics` to
`none` and give `particlization.parameters.input_file` the path to your
`freeze_out.dat`.

## Jets

Dijets can be sampled from the event's collision geometry and evolved in CCAKE.
The production vertices come from either **AMPT** (`vertex_source: binary` or
`minijet`, needs an AMPT IC) or **TRENTo** (`vertex_source: trento`, needs a
TRENTo IC with `ncoll: true`) — see [pbpb_5p02_trento_jets](pbpb_5p02_trento_jets/)
for the TRENTo path. To embed sampled dijets, add to `input.hydrodynamics`:

```yaml
    jets_sampling:
      enabled: true
      n_dijets: 1
      pt_min: 100.0
      pt_max: 200.0
    hydro:
      jets:
        type: BBMG          # initialize + propagate BBMG jets in CCAKE
        Energy_scaling: 0
        Path_Length_scaling: 1
      # to deposit the jet energy loss back into the fluid, also couple a source:
      source:
        type: jet
        model: BBMG
        smearing_radius: 0.5
```

`jets_sampling` runs `utils/sample_dijets` on the event's AMPT geometry and
points `hydro.jets.input_mode: file` at the result; `hydro.jets.type: BBMG`
then evolves those jets, and the optional `hydro.source` block couples their
energy loss into the hydro (mirrors CCAKE's `config_jet_ampt_3d.yaml`). See
`utils/sample_dijets/README.md` for the physics and file formats.
