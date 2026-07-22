"""Scalar observables extracted from a chain event, used by the T2
fixed-seed regression (test_references.py / regenerate_references.py).

Deliberately robust quantities: totals from conservation.dat (known format),
line counts, and summed IC energy density — insensitive to column additions
in the more volatile per-particle files.
"""
import os


def compute_observables(output_dir):
    obs = {}

    cons = os.path.join(output_dir, 'event_0', 'ccake', 'conservation.dat')
    with open(cons) as f:
        f.readline()  # header: t Eloss S Btotal Stotal Qtotal
        rows = [[float(x) for x in line.split()] for line in f if line.strip()]
    obs['entropy_initial'] = rows[0][2]
    obs['entropy_final'] = rows[-1][2]
    obs['btotal_initial'] = rows[0][3]
    obs['hydro_end_time'] = rows[-1][0]

    fo = os.path.join(output_dir, 'event_0', 'ccake', 'freeze_out.dat')
    with open(fo) as f:
        obs['n_freezeout_cells'] = sum(
            1 for line in f if line.strip() and not line.startswith('#'))

    ic = os.path.join(output_dir, 'event_0', 'amptgenesis', 'ccake_ic.dat')
    total_e, n_cells = 0.0, 0
    with open(ic) as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            total_e += float(line.split()[3])
            n_cells += 1
    obs['ic_total_energy_density'] = total_e
    obs['ic_n_cells'] = n_cells
    return obs
