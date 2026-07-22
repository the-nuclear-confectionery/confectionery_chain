# Pb+Pb 5.02 TeV — TRENTo → CCAKE (charge-less, entropy input)

The simplest hydro path — no overlay, no conserved charges:

```
TRENTo (entropy deposition, 0-5% central)
  -> CCAKE (2+1)D viscous hydro, charge-less, reads entropy directly
  -> BQSSampler (Cooper-Frye sampling, no chemical potentials)
  -> SMASH (resonance decays only)
  -> qvector_writter (charged + identified Q-vectors, ROOT output)
```

## Physics case

Central Pb+Pb at 5.02 TeV, boost-invariant, with the TRENTo entropy profile
handed straight to CCAKE (`input_as_entropy: true`) and no B/S/Q evolution.
This is the cheapest and most robust chain — a good first thing to run to
confirm an install works end to end. Uses the shipped Houston EoS tables
(`normalize_by_T: true`), so no external EoS is needed.

## Run it

```sh
conda activate <chain env>
sed -i 's|<REPLACE:/path/to/test_chain>|'"$PWD"'|' examples/pbpb_5p02_trento_ccake/config.yml
# also set the output/tmp paths, then:
python wrapper/main.py 0 pbpb_5p02.db examples/pbpb_5p02_trento_ccake/config.yml
```

## Expectations

- Fine 0.1 fm transverse grid, boost-invariant: O(minutes–tens of minutes)
  per event for hydro on a single node.
- Per-event outputs in `<output>/event_0/`: `trento/ccake_ic.dat`,
  `ccake/freeze_out.dat`, sampled particle list, `smash/`, `q_0.root`.
