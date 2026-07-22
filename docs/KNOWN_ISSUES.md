# Known issues

Open, understood-but-not-yet-fixed problems in the chain. Each entry: what
breaks, the impact, the current workaround, and what a real fix needs. Keep
new findings here rather than scattering them across commit messages.

---

## 0. CCAKE segfaults on grid overflow (size the grid generously)

**Status:** open, mitigated by config. **Severity:** hard crash (SIGSEGV) mid-run.

CCAKE SIGSEGVs when radial/longitudinal outflow reaches the edge of the SPH
grid — it does not gracefully delete particles that leave the domain. Observed
as a late-time crash (~t=14 fm/c) after an otherwise healthy evolution: a
±10 fm transverse grid overflows for both central Au+Au (19.6 GeV) and Pb+Pb
(5.02 TeV). `buffer_particles` (which would pad the edge) is **non-functional
in the current CCAKE build**, so it cannot rescue this.

**Root cause + fix applied:** CCAKE's auxiliary *neighbour* grid
(`src/system_state.cpp`, `reset_neighbour_list`) was hardcoded to **2×** the
initial domain; the post-freeze-out remnant expands past it and the Cabana
neighbour lookup goes out of bounds → SIGSEGV (exit 139/148). Freeze-out is
already complete when this happens (the surface is written; it prints "0
freeze-out particles"), so nothing physical is lost — CCAKE is just grinding
on a dead remnant. **Changed the factor to 4×** (a ±14 config domain → ±56
neighbour grid), which lets the remnant evolve to `max_tau` without overflow.
This is a local modification to the CCAKE submodule — push it upstream.

**Alternative workarounds (no code change):** cap `max_tau` (~15 for central
Pb+Pb — freeze-out is done by then; the pbpb example uses this), or use a large
config grid. `buffer_particles` would also help but is non-functional in the
current CCAKE build.

---

## 1. AMPT per-event RNG bias — FIXED upstream (AMPT f5d8123)

**Status:** resolved. **Severity:** was a physics bias for symmetric systems.

Running AMPT one event per process (`NEVNT=1`) used to inject a spurious
forward (+η) bias — **~+3 charged particles/event at midrapidity (~15σ at
100k events)** in symmetric O+O (true value 0). Cause: AMPT seeded its
generators once per process before the event loop; several restarted from
fixed/default seeds (PYTHIA `RLU`, ZPC `ran1`) and the HIJING LCG had a
correlated head, so one-event-per-process correlated every event the same way.

**Fixed in AMPT commit `f5d8123`** (now the pinned submodule tip): all
generators are reseeded from `NSEED` at event start — HIJING/ART `RANART`
switched to splitmix64 (`SEEDART`), and PYTHIA `RLU` / ZPC `iseedp` reseeded
via `IHASH(NSEED, salt)` (`main.f`, `amptsub.f`). One-event-per-process
(`NEVNT=1`, the mode the wrapper uses) is now properly decorrelated.

Notes for the wrapper (`ampt_initial_condition.py`): input.ampt format is
unchanged, so no wrapper change is needed. With `ihjsed=0` (the default),
`NSEED` = the wrapper's `hijing_seed`, which now drives *all* generators —
so a run is fully reproducible from that one seed. The wrapper's separate
`parton_cascade_seed` is now overridden by `IHASH(NSEED)` (harmless, just
redundant). Original analysis:
`~/git_repos/test/test2/AMPT/AMPT_per_event_RNG_bias_findings.md`.

---

## 2. Free-streaming (FS) preequilibrium discards cells it should keep

**Status:** open, deferred. **Severity:** wrong IC handed to hydro when FS is on.

The free-streaming preequilibrium stage
(`wrapper/specializations/freestreaming_preequilibrium.py`) throws away
material it should not — cells that should survive free-streaming to `tau_hydro`
are being dropped, so the energy/entropy handed to CCAKE is short of what went
in. This makes the `TRENTO → FS → BQSSampler → SMASH → qvector` chain
unreliable, which is why it is the last of the target chains to bring online.

**Workaround now:** prefer the no-FS paths (`TRENTO → CCAKE` with
`input_as_entropy`, or `TRENTO → ICCING → CCAKE`) until FS is fixed.

**Real fix (later):** audit the free-stream grid/cell handling — identify which
cells are dropped and why (cutoff, grid bounds, or the freestream→ccake_ic
conversion) and preserve them.

---

## 3. `critical_scaling_bulk` vs `critical_scaling_enabled` key mismatch

**Status:** open, minor/harmless. **Severity:** cosmetic (silently ignored).

CCAKE's `input.cpp` reads the bulk critical-scaling flag as
`hydro.viscous_parameters.bulk.critical_scaling_enabled`, but both this
chain's wrapper/schema **and** CCAKE's own reference configs write
`critical_scaling_bulk`. The written key is therefore ignored and the flag
falls back to its default (`false`). Harmless as long as critical bulk scaling
is off (the usual case), but the two names should be reconciled — either patch
CCAKE to read `critical_scaling_bulk`, or switch the configs/schema to
`critical_scaling_enabled`.
