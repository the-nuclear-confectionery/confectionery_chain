#!/usr/bin/env python3
"""Sample back-to-back dijets from AMPT events.

Kinematics come from PYTHIA HardQCD (partonic-only); production vertices come
from AMPT event geometry (binary collisions or minijets).

Usage:
    python sample_dijets.py \\
        --ampt-dir AMPT_evt0008 \\
        --vertex-source binary \\
        --n-dijets 10 \\
        --pt-min 5 --pt-max 50 \\
        --seed 42 \\
        --output dijets.csv

PYTHIA is required for kinematics (`import pythia8`). On ctop10 ensure
PYTHONPATH points at the pythia8 install before running.
"""
import argparse
import csv
import math
import sys
from pathlib import Path

import numpy as np


# Speed of light = 1 (natural units throughout, distances in fm, times in fm/c)


def beam_velocity(sqrts, m_p=0.938):
    """Lab-frame speed of each beam nucleus |v| = sqrt(1 - (2m_p/sqrt(s))^2)."""
    return math.sqrt(1.0 - (2.0 * m_p / sqrts) ** 2)


# ─────────────────────────────────────────────────────────────────────────────
# AMPT Input Parsing
# ─────────────────────────────────────────────────────────────────────────────

def read_beam_energy(ampt_dir):
    """Parse sqrt(s_NN) from <ampt_dir>/input.ampt. Returns float or None."""
    input_ampt = ampt_dir / "input.ampt"
    if not input_ampt.exists():
        return None
    sqrts, frame = None, None
    for line in input_ampt.read_text().splitlines():
        if "!" not in line:
            continue
        value_part, comment = line.split("!", 1)
        tokens = value_part.split()
        if not tokens:
            continue
        if "EFRM" in comment and sqrts is None:
            sqrts = float(tokens[0])
        elif "FRAME" in comment and frame is None:
            frame = tokens[0]
    if sqrts is None:
        return None
    if frame is not None and frame.upper() != "CMS":
        raise SystemExit(
            f"AMPT FRAME={frame!r} in {input_ampt}; this script assumes CMS."
        )
    return sqrts


def parse_binary_collisions(path, sqrts, m_p=0.938):
    """Parse ana/binary-collisions.dat (written by patched HIJING).

    Format:
      Header : event_id  NCOLT
      Per collision: JP  JT  x_c  y_c  z_P_rest  z_T_rest   (all fm)

    Returns arrays (xs, ys, zs_lab, ts) where ts is collision time [fm/c].
    """
    gamma = sqrts / (2.0 * m_p)
    xs, ys, zs = [], [], []
    with open(path) as f:
        for line in f:
            toks = line.split()
            if len(toks) == 2:          # header: event_id NCOLT
                continue
            if len(toks) < 6:
                continue
            try:
                x_c      = float(toks[2])
                y_c      = float(toks[3])
                z_P_rest = float(toks[4])
                z_T_rest = float(toks[5])
            except (ValueError, IndexError):
                print(f"[warn] skipping malformed line in {path}: {line.strip()}", file=sys.stderr)
                continue
            xs.append(x_c)
            ys.append(y_c)
            zs.append((z_P_rest, z_T_rest))

    if not xs:
        raise SystemExit(f"No binary collision rows found in {path}")

    xs = np.asarray(xs)
    ys = np.asarray(ys)
    z_pairs = np.asarray(zs)

    z_P_all = z_pairs[:, 0]
    z_T_all = z_pairs[:, 1]

    # Global front-face positions (same shift HIJING uses for all nucleons)
    z_P_max = z_P_all.max()
    z_T_max = z_T_all.max()

    z_P_lab = (z_P_all - z_P_max) / gamma   # ≤ 0
    z_T_lab = (z_T_max - z_T_all) / gamma   # ≥ 0
    zs_lab  = (z_P_lab + z_T_lab) / 2.0

    # Collision time in lab frame
    v_beam = beam_velocity(sqrts, m_p)
    ts = (z_T_lab - z_P_lab) / (2.0 * v_beam)

    return xs, ys, zs_lab, ts


def parse_minijet(path):
    """Parse minijet-initial-beforePropagation.dat. Returns (xs, ys, zs) [fm]."""
    with open(path) as f:
        f.readline()  # event header
        xs, ys, zs = [], [], []
        for line in f:
            toks = line.split()
            if len(toks) < 9:
                continue
            xs.append(float(toks[5]))
            ys.append(float(toks[6]))
            zs.append(float(toks[7]))
    return np.asarray(xs), np.asarray(ys), np.asarray(zs)


def parse_trento_ncoll(path):
    """Parse TRENTo ncoll_list{n}.dat (transverse "x y" midpoints of binary
    collisions, written when ncoll = true). Returns (xs, ys) [fm]."""
    xs, ys = [], []
    with open(path) as f:
        for line in f:
            toks = line.split()
            if len(toks) < 2:
                continue
            xs.append(float(toks[0]))
            ys.append(float(toks[1]))
    return np.asarray(xs), np.asarray(ys)


# ─────────────────────────────────────────────────────────────────────────────
# Vertex Sampling
# ─────────────────────────────────────────────────────────────────────────────

def make_vertex_sampler(args, rng, sqrts):
    """Return a function n -> (xs, ys, zs, ts) for the chosen --vertex-source."""
    ampt_dir = Path(args.ampt_dir)
    ana = ampt_dir / "ana"
    src = args.vertex_source

    if src == "binary":
        bc_path = ana / "binary-collisions.dat"
        if not bc_path.exists():
            raise SystemExit(
                f"{bc_path} not found.\n"
                "Run AMPT with the patched hijing1.383_ampt.f that writes\n"
                "ana/binary-collisions.dat (unit 93)."
            )
        xs, ys, zs, ts = parse_binary_collisions(bc_path, sqrts)
        n_coll = len(xs)
        v_b = beam_velocity(sqrts)
        print(f"[info] loaded {n_coll} binary collision vertices from {bc_path}  "
              f"t_coll ∈ [{ts.min():.3f}, {ts.max():.3f}] fm/c  "
              f"(v_beam = {v_b:.5f}c)",
              file=sys.stderr)

        def sampler(n):
            if n > n_coll:
                print(f"[warn] N={n} > #binary collisions={n_coll}; "
                      "sampling with replacement.", file=sys.stderr)
            idx = rng.integers(0, n_coll, size=n)
            return xs[idx], ys[idx], zs[idx], ts[idx]

        return sampler

    if src == "minijet":
        xs, ys, zs = parse_minijet(ana / "minijet-initial-beforePropagation.dat")
        if len(xs) == 0:
            raise SystemExit("No minijets found.")
        print(f"[info] loaded {len(xs)} minijets", file=sys.stderr)

        def sampler(n):
            if n > len(xs):
                print(f"[warn] N={n} > #minijets={len(xs)}; "
                      "sampling with replacement.", file=sys.stderr)
            idx = rng.integers(0, len(xs), size=n)
            return xs[idx], ys[idx], zs[idx], np.zeros(n)

        return sampler

    if src == "trento":
        # TRENTo binary collisions: transverse (x,y) midpoints at z = t = 0
        # (boost-invariant; free-streamed to tau_hydro downstream).
        nc_path = ampt_dir / "ncoll_list0.dat"
        if not nc_path.exists():
            raise SystemExit(
                f"{nc_path} not found.\n"
                "Run TRENTo with ncoll = true so it writes ncoll_list0.dat."
            )
        xs, ys = parse_trento_ncoll(nc_path)
        if len(xs) == 0:
            raise SystemExit("No TRENTo binary collisions found.")
        print(f"[info] loaded {len(xs)} TRENTo binary collisions from {nc_path}",
              file=sys.stderr)

        def sampler(n):
            if n > len(xs):
                print(f"[warn] N={n} > #binary collisions={len(xs)}; "
                      "sampling with replacement.", file=sys.stderr)
            idx = rng.integers(0, len(xs), size=n)
            return xs[idx], ys[idx], np.zeros(n), np.zeros(n)

        return sampler

    raise SystemExit(f"Unknown --vertex-source: {src!r}")


# ─────────────────────────────────────────────────────────────────────────────
# PYTHIA
# ─────────────────────────────────────────────────────────────────────────────

def init_pythia(sqrts, pt_min, pt_max, seed):
    try:
        import pythia8
    except ImportError as exc:
        raise SystemExit(
            "pythia8 is not importable.\n"
            f"  underlying error: {exc}\n"
            "On ctop10 set PYTHONPATH to the PYTHIA install, e.g.\n"
            "    export PYTHONPATH=/path/to/pythia8/lib:$PYTHONPATH"
        )
    p = pythia8.Pythia()
    for cmd in [
        "HardQCD:all = on",
        f"PhaseSpace:pTHatMin = {pt_min}",
        f"PhaseSpace:pTHatMax = {pt_max}",
        "PartonLevel:ISR = off",
        "PartonLevel:FSR = off",
        "PartonLevel:MPI = off",
        "HadronLevel:all = off",
        "Beams:idA = 2212",
        "Beams:idB = 2212",
        f"Beams:eCM = {sqrts}",
        "Random:setSeed = on",
        f"Random:seed = {seed}",
        "Print:quiet = on",
        "Init:showProcesses = off",
        "Init:showChangedSettings = off",
        "Init:showChangedParticleData = off",
        "Init:showMultipartonInteractions = off",
        "Next:numberCount = 0",
        "Next:numberShowEvent = 0",
        "Next:numberShowInfo = 0",
        "Next:numberShowProcess = 0",
        "Next:numberShowLHA = 0",
    ]:
        p.readString(cmd)
    if not p.init():
        raise SystemExit("PYTHIA failed to initialize.")
    return p


def parton_kinematics(p):
    px, py, pz, E = p.px(), p.py(), p.pz(), p.e()
    pT = math.hypot(px, py)
    phi = math.atan2(py, px)
    y = 0.5 * math.log((E + pz) / (E - pz)) if (E - pz) > 0 else 0.0
    p_abs_sq = px * px + py * py + pz * pz
    p_abs = math.sqrt(p_abs_sq)
    eta = 0.5 * math.log((p_abs + pz) / (p_abs - pz)) if (p_abs - pz) > 0 else 0.0
    return pT, phi, y, eta


# ─────────────────────────────────────────────────────────────────────────────
# Free-streaming
# ─────────────────────────────────────────────────────────────────────────────

def free_stream(x_c, y_c, z_c, t_c, px, py, pz, E, tau_hydro):
    """Free-stream a massless parton from (x_c, y_c, z_c, t_c) to Milne time τ_hydro.

    The parton moves on a straight worldline. We solve for the lab time t_fs
    such that τ(t_fs) ≡ sqrt(t_fs² - z(t_fs)²) = τ_hydro.

    Parameters
    ----------
    x_c, y_c, z_c, t_c : float   production vertex  [fm, fm/c]
    px, py, pz, E       : float   4-momentum  [GeV]
    tau_hydro           : float   Milne time of hydro initialisation  [fm/c]

    Returns
    -------
    x_fs, y_fs, z_fs : float   transverse + longitudinal position at τ_hydro  [fm]
    t_fs             : float   lab time at τ_hydro  [fm/c]
    eta_s_fs         : float   spacetime rapidity at τ_hydro
    late             : bool    True if parton was produced AFTER τ_hydro
    """
    # Proper time at production vertex
    tau_prod = math.sqrt(max(0.0, t_c * t_c - z_c * z_c))
    if tau_prod >= tau_hydro:
        # Parton created after hydro starts; return production vertex as-is
        eta_s = math.atanh(min(0.9999, abs(z_c / t_c))) if abs(t_c) > 1e-12 else 0.0
        return x_c, y_c, z_c, t_c, eta_s, True

    beta_z = pz / E
    delta_z = z_c - beta_z * t_c
    denom   = 1.0 - beta_z * beta_z

    disc = delta_z * delta_z + denom * tau_hydro * tau_hydro
    t_fs = (beta_z * delta_z + math.sqrt(disc)) / denom

    dt = t_fs - t_c
    x_fs   = x_c + (px / E) * dt
    y_fs   = y_c + (py / E) * dt
    z_fs   = z_c + beta_z * dt
    z_t_ratio = z_fs / t_fs if abs(t_fs) > 1e-12 else 0.0
    eta_s_fs = math.atanh(min(0.9999, abs(z_t_ratio))) * (1 if z_t_ratio >= 0 else -1) if abs(t_fs) > 1e-12 else 0.0

    return x_fs, y_fs, z_fs, t_fs, eta_s_fs, False


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--ampt-dir", required=True,
                        help="AMPT event directory (containing ana/ and input.ampt).")
    parser.add_argument("--vertex-source", required=True,
                        choices=["binary", "minijet", "trento"],
                        help="Source of parton production vertices.")
    parser.add_argument("--n-dijets", type=int, required=True,
                        help="Number of dijets to sample.")
    parser.add_argument("--pt-min", type=float, default=5.0,
                        help="Minimum parton pT [GeV].")
    parser.add_argument("--pt-max", type=float, default=50.0,
                        help="Maximum parton pT [GeV].")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed.")
    parser.add_argument("--sqrts", type=float, default=None,
                        help="Override sqrt(s_NN) in GeV. Auto-read from input.ampt if absent.")
    parser.add_argument("--min-dy", type=float, default=0.0,
                        help="reject dijets with |y1 - y2| <= this (rapidity separation cut)")
    parser.add_argument("--tau-hydro", type=float, default=None,
                        help="Milne time τ₀ [fm/c] at which hydro starts. "
                             "If given, free-streams each parton to τ₀.")
    parser.add_argument("--output", default="dijets.csv",
                        help="Output CSV file.")
    args = parser.parse_args()

    ampt_dir = Path(args.ampt_dir)
    if not ampt_dir.is_dir():
        raise SystemExit(f"--ampt-dir is not a directory: {ampt_dir}")

    sqrts = args.sqrts if args.sqrts is not None else read_beam_energy(ampt_dir)
    if sqrts is None:
        raise SystemExit(
            f"No input.ampt found in {ampt_dir}; pass --sqrts manually."
        )
    print(f"[info] sqrt(s_NN) = {sqrts} GeV")
    print(f"[info] vertex source: {args.vertex_source}")
    print(f"[info] N dijets: {args.n_dijets}, pT ∈ [{args.pt_min}, {args.pt_max}] GeV")

    tau_hydro = args.tau_hydro
    if tau_hydro is not None:
        print(f"[info] tau_hydro = {tau_hydro} fm/c (free-streaming enabled)")

    rng = np.random.default_rng(args.seed)
    vertex_sampler = make_vertex_sampler(args, rng, sqrts)
    xs_vtx, ys_vtx, zs_vtx, ts_vtx = vertex_sampler(args.n_dijets)

    pythia = init_pythia(sqrts, args.pt_min, args.pt_max, args.seed)

    rows = []
    n_done = 0
    n_attempted = 0
    n_late = 0
    max_attempts = max(100, 50 * args.n_dijets)
    while n_done < args.n_dijets:
        n_attempted += 1
        if n_attempted > max_attempts:
            raise SystemExit(
                f"PYTHIA produced {n_done}/{args.n_dijets} dijets in "
                f"{n_attempted} attempts. Check pT range vs sqrt(s)."
            )
        if not pythia.next():
            continue
        hard = [p for p in pythia.event if abs(p.status()) == 23]
        if len(hard) != 2:
            continue

        # rapidity-separation cut: reject dijets with |y1 - y2| <= min_dy
        if args.min_dy > 0.0:
            _, _, y0, _ = parton_kinematics(hard[0])
            _, _, y1, _ = parton_kinematics(hard[1])
            if abs(y0 - y1) <= args.min_dy:
                continue

        x_vtx = float(xs_vtx[n_done])
        y_vtx = float(ys_vtx[n_done])
        z_vtx = float(zs_vtx[n_done])
        t_vtx = float(ts_vtx[n_done])

        for pidx, p in enumerate(hard):
            pT, phi, y_rap, eta = parton_kinematics(p)
            row = [
                n_done, pidx, p.id(), p.m(),
                x_vtx, y_vtx, z_vtx, t_vtx,
                p.px(), p.py(), p.pz(), p.e(),
                pT, phi, y_rap, eta,
            ]

            if tau_hydro is not None:
                x_fs, y_fs, z_fs, t_fs, eta_s_fs, late = free_stream(
                    x_vtx, y_vtx, z_vtx, t_vtx,
                    p.px(), p.py(), p.pz(), p.e(),
                    tau_hydro,
                )
                if late:
                    n_late += 1
                row.extend([x_fs, y_fs, z_fs, t_fs, eta_s_fs, int(late)])

            rows.append(row)
        n_done += 1

    if n_late:
        print(f"[warn] {n_late} parton(s) born after τ_hydro; "
              "free-streamed to production vertex (late=1).",
              file=sys.stderr)

    cols = [
        "dijet_id", "parton_idx", "pid", "mass",
        "x_vtx", "y_vtx", "z_vtx", "t_vtx",
        "px", "py", "pz", "E",
        "pT", "phi", "y", "eta",
    ]
    if tau_hydro is not None:
        cols += ["x_fs", "y_fs", "z_fs", "t_fs", "eta_s_fs", "late"]

    with open(args.output, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    print(f"[info] wrote {n_done} dijets ({len(rows)} parton rows) to {args.output}")


if __name__ == "__main__":
    main()
