# sample_dijets

Samples back-to-back dijets for injection into CCAKE initial conditions.
Kinematics come from PYTHIA8 HardQCD (partonic only, ISR/FSR off) in a
configurable pT-hat window; production vertices are drawn from the event
geometry — AMPT binary collisions or minijets, or TRENTo binary collisions
(`ncoll_list0.dat`, needs `ncoll = true`) — so the dijets are embedded
consistently in the event that sourced the hydro background. For TRENTo
(boost-invariant) the collisions are placed at `z = t = 0` and free-streamed
to `tau_hydro`.

## Build

Built by `./chain install` (or `./chain rebuild sample_dijets`). Manually:

```sh
make PYTHIA8=$PYTHIA8DIR      # PYTHIA8DIR is set by the chain conda env
```

## Run

```sh
./sample_dijets my_run.conf   # see sample_dijets.conf.example
```

Output CSV columns:

```
dijet_id,parton_idx,pid,mass,x_vtx,y_vtx,eta_s,tau,p0,p1,p2,p3,pT,phi,y,eta
```

Positions are Milne coordinates (fm, spacetime rapidity); momenta in GeV.
With `tau_hydro > 0` the partons are free-streamed from their production
point to that proper time, which should match the hydro starting time
(`global.tau_hydro` in the chain config).

## Chain integration

Enable per-event sampling in a chain config under
`input.hydrodynamics.jets_sampling`; the wrapper runs this tool on the
event's AMPT output, converts the CSV to CCAKE's jets-file format
(`x y eta pT phi rapidity`), and points `hydro.jets.input_mode: file` at it.
See the schema (`wrapper/utils/schema.yml`) for the available keys.

`sample_dijets.py` is a standalone Python twin of the C++ tool (same physics,
argparse CLI) useful for interactive exploration; the chain uses the C++
binary.
