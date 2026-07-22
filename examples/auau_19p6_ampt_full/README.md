# Au+Au 19.6 GeV — full AMPT chain

The complete AMPT-based pipeline at a Beam Energy Scan energy:

```
AMPT (IC + parton transport)
  -> AMPTGenesis (smear partons onto the hydro grid, Milne coordinates)
  -> CCAKE (3+1)D viscous hydro with B, S, Q charge evolution
  -> BQSSampler (Cooper-Frye sampling with BSQ chemical potentials)
  -> SMASH (resonance decays only)
  -> qvector_writter (charged + identified Q-vectors, ROOT output)
```

## Physics case

Central (b < 3.3 fm ≈ 0–5%) Au+Au at 19.6 GeV. At BES energies baryon
stopping makes the conserved-charge densities (B, S, Q) dynamically relevant,
so charge evolution and the BSQ sampler are on. The AMPTGenesis `K` smearing
normalization is the calibration knob against measured dNch/deta.

## Run it

```sh
conda activate <chain env>
sed -i 's|<REPLACE:/path/to/test_chain>|'"$PWD"'|' examples/auau_19p6_ampt_full/config.yml
# also set the output/tmp paths, then:
python wrapper/main.py 0 auau_19p6.db examples/auau_19p6_ampt_full/config.yml
```

## Expectations

- One event end-to-end takes O(1 h) on a single node at this grid spacing
  (dominated by 3+1D CCAKE); the tiny-grid twin in `tests/t1/` runs in minutes.
- Per-event outputs land in `<output>/event_0/`: `ampt/` (parton files +
  `binary-collisions.dat`), `amptgenesis/ccake_ic.dat`, `ccake/freeze_out.dat`,
  sampled particle lists, `smash/`, and `q_*.root` Q-vector files.
- Event metadata (seeds, stage types, centrality estimator) is recorded in the
  SQLite database passed on the command line.

## Variations

- **Jets**: add an `input.hydrodynamics.jets_sampling` block (see
  `utils/sample_dijets/README.md`) plus `hydro.jets` BBMG parameters to embed
  sampled dijets into this event's initial condition.
- **Centrality**: widen `BMIN`/`BMAX`, or run min-bias with `BMAX: 50`.
