# Au+Au @ 19.6 GeV — AMPT with a continuous source term into CCAKE

`AMPT → AMPTGenesis (τ₀ IC) → CCAKE (3+1D + AMPT source) → BQSSampler → SMASH decays → Q-vectors`

Same setup as [auau_19p6_ampt_full](../auau_19p6_ampt_full/), but instead of
folding *all* AMPT partons onto the τ₀ surface, the partons that form **after**
τ₀ are injected into the running hydro as a source term (`hydro.source`, mirroring
CCAKE's `input_ampt.yaml`). This is the physically correct treatment of
late-forming partons at BES energies.

**Physics case:** baryon-rich (3+1)D BES Au+Au with a time-dependent AMPT source.

**Key knobs:**
- `overlay.parameters.smearing.backpropagate: false` — late partons go to the
  source, not the IC.
- `hydro.source.{type: ic, model: AMPT, file: …}` — the source reads this event's
  AMPT parton output (`event_<id>/ampt/parton-initial-afterPropagation.dat`).
  **Set `file` to that path** (it is per-event; the config points at event 0).
- `output.print_conservation_state: true` — sources inject energy/charge, so watch
  conservation.

**Run:**
```sh
python wrapper/main.py 0 auau_19p6.db examples/auau_19p6_ampt_source/config.yml
```

Needs a baryon-rich EoS for accurate high-μ_B physics — see the note in
[auau_19p6_ampt_full](../auau_19p6_ampt_full/README.md).
