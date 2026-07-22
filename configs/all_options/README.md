# All-options reference configs

One config per chain **module**, each listing **every flag** that module accepts,
with its schema default value and a one-line description. These are exhaustive
**flag catalogs**, not tuned physics runs — use them to discover what a module
can do, then copy the keys you need into a runnable chain config in
[`../../examples/`](../../examples/).

Every file here is generated directly from `wrapper/utils/schema.yml`, so it can
never drift from or omit a real option. To refresh after editing the schema:

```sh
python configs/all_options/regenerate.py
```

| File | Module | Stage |
|---|---|---|
| `trento.yaml` | TRENTo | initial condition |
| `ampt.yaml` | AMPT | initial condition |
| `iccing.yaml` | ICCING | overlay |
| `amptgenesis.yaml` | AMPTGenesis | overlay |
| `freestreaming.yaml` | free-streaming | pre-equilibrium |
| `ccake.yaml` | CCAKE | hydrodynamics |
| `is3d.yaml` | iS3D | particlization |
| `bqssampler.yaml` | BQSSampler | particlization |
| `analytical.yaml` | analytical Cooper-Frye | particlization |
| `smash.yaml` | SMASH | afterburner |
| `afterdecays.yaml` | afterdecays | afterburner |
| `qvector_writter.yaml` | qvector_writter | analysis |

Notes:
- The values shown are the **schema defaults**. A few keys have no default (marked
  `[no schema default]`) and show a placeholder — set them yourself.
- Each file is a complete, schema-valid config (a minimal `global` plus the one
  module), so the T0 suite validates it, but it is a reference — not a physics run
  (you would never enable every option at once).
- `options: [...]` in a comment lists the allowed enum values for that key.
