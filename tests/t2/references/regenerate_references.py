#!/usr/bin/env python
"""Regenerate the fixed-seed reference observables for the T2 regression test.

Runs the auau_tiny chain with its fixed seeds and records robust scalar
observables plus the submodule provenance that produced them. Run this
deliberately — e.g. after an intentional physics change — then commit the
updated yaml.

Usage:  python tests/t2/references/regenerate_references.py
"""
import os
import subprocess
import sys
import tempfile

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
T2 = os.path.dirname(HERE)
TESTS = os.path.dirname(T2)
REPO = os.path.dirname(TESTS)
sys.path.insert(0, TESTS)
sys.path.insert(0, T2)

from conftest import resolve_config, run_chain_event  # noqa: E402
from observables import compute_observables  # noqa: E402

TOLERANCES = {
    'entropy_initial': 0.02,
    'entropy_final': 0.02,
    'btotal_initial': 0.02,
    'hydro_end_time': 0.05,
    'n_freezeout_cells': 0.10,
    'ic_total_energy_density': 0.02,
    'ic_n_cells': 0.02,
}


def submodule_provenance():
    out = subprocess.run(['git', 'submodule', 'status'], cwd=REPO,
                         capture_output=True, text=True, check=True).stdout
    return {line.split()[1]: line.split()[0].lstrip('+-U')
            for line in out.strip().splitlines()}


def main():
    with tempfile.TemporaryDirectory() as workdir:
        config_path, output_dir = resolve_config(
            os.path.join(TESTS, 't1', 'configs', 'auau_tiny.yml'), workdir)
        print("running fixed-seed auau_tiny chain ...")
        proc, log_path = run_chain_event(config_path, workdir, timeout=7200)
        if proc.returncode != 0:
            sys.exit(f"chain failed — see {log_path}")

        reference = {
            'config': 'tests/t1/configs/auau_tiny.yml',
            'observables': compute_observables(output_dir),
            'tolerances': TOLERANCES,
            'provenance': submodule_provenance(),
        }

    out_path = os.path.join(HERE, 'auau_tiny.yml')
    with open(out_path, 'w') as f:
        yaml.dump(reference, f, default_flow_style=False, sort_keys=False)
    print(f"wrote {out_path}")


if __name__ == '__main__':
    main()
