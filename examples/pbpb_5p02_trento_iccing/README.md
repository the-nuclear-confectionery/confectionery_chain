# Pb+Pb 5.02 TeV — TRENTo + ICCING chain

The LHC-energy pipeline with initial-state charge fluctuations:

```
TRENTo (entropy deposition, 0-5% central)
  -> ICCING (gluon splitting -> B, S, Q charge deposition)
  -> CCAKE (2+1)D viscous hydro with BSQ charge evolution
  -> iS3D (Cooper-Frye particlization)
  -> SMASH (resonance decays only)
  -> qvector_writter (charged + identified Q-vectors, ROOT output)
```

## Physics case

Central Pb+Pb at 5.02 TeV, boost-invariant. ICCING converts the smooth
TRENTo profile into an event-by-event charge-fluctuating initial state, which
is what makes the BSQ charge evolution in CCAKE non-trivial at the LHC.

## Run it

```sh
conda activate <chain env>
sed -i 's|<REPLACE:/path/to/test_chain>|'"$PWD"'|' examples/pbpb_5p02_trento_iccing/config.yml
# also set the output/tmp paths, then:
python wrapper/main.py 0 pbpb_5p02.db examples/pbpb_5p02_trento_iccing/config.yml
```

Centrality classes via `centrality-min`/`centrality-max` need a pre-computed
TRENTo entropy dictionary (`entropy-dict-dir`). Without one, select events by
impact parameter instead (`b-min`/`b-max`) — the tiny-grid twin in `tests/t1/`
does exactly that.

## Expectations

- Fine 0.06 fm transverse grid: O(tens of minutes) per event for the hydro
  stage on a single node; the `tests/t1/` twin runs in minutes on a coarse grid.
- Per-event outputs in `<output>/event_0/`: `trento/`, `iccing/densities0.dat`,
  `ccake/freeze_out.dat`, iS3D particle lists, `smash/`, `q_*.root`.
