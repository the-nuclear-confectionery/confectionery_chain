#!/usr/bin/env python
"""Regenerate references/observables.yml — the fixed-seed physics-observable
references for test_observables.py.

Restarts each system from its gold-standard freeze-out surface with fixed seeds
(BQSSampler -> SMASH decays-only -> qvector) and records dNch/deta, <pT>, v2, v3
plus submodule provenance. Run deliberately after an intentional physics change.

  CHAIN_GOLD_SURFACES_DIR=<dir with auau/pbpb_freeze_out.dat> \
      python tests/t2/references/regenerate_observables.py
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

from conftest import run_chain_event                    # noqa: E402
from observable_runs import SYSTEMS, build_config, surface_path  # noqa: E402
from flow_observables import compute_flow_observables   # noqa: E402

TOLERANCES = {'dNch_deta_mid': 0.05, 'mean_pt_charged': 0.03, 'v2': 0.15, 'v3': 0.20}


def provenance():
    out = subprocess.run(['git', 'submodule', 'status'], cwd=REPO,
                         capture_output=True, text=True, check=True).stdout
    keep = ('CCAKE', 'BQSSampler', 'smash', 'qvector', 'AMPT')
    return {l.split()[1]: l.split()[0].lstrip('+-U')
            for l in out.strip().splitlines() if any(k in l for k in keep)}


def main():
    systems = {}
    for name in sorted(SYSTEMS):
        surf = surface_path(name)
        if not os.path.isfile(surf):
            sys.exit(f"gold surface missing (set CHAIN_GOLD_SURFACES_DIR): {surf}")
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as workdir:
            cfg = build_config(name, REPO, os.path.join(workdir, 'out'),
                               os.path.join(workdir, 'tmp'))
            cfg_path = os.path.join(workdir, 'config.yml')
            with open(cfg_path, 'w') as f:
                yaml.dump(cfg, f)
            print(f"running {name} ({SYSTEMS[name]['samples']} samples) ...")
            proc, log = run_chain_event(cfg_path, workdir, timeout=10800)
            if proc.returncode != 0:
                sys.exit(f"{name} failed — see {log}")
            obs = compute_flow_observables(os.path.join(workdir, 'out', 'q_0.root'))
        systems[name] = {'surface': SYSTEMS[name]['surface'],
                         'samples': SYSTEMS[name]['samples'],
                         'afterburner': 'decays_only',
                         'observables': obs}

    ref = {
        'description': ('T2 physics-observable references (fixed-seed restart-from-surface: '
                        'BQSSampler -> SMASH decays-only -> qvector). v_n are integrated '
                        'event-plane values at |eta|<0.5.'),
        'systems': systems,
        'tolerances': TOLERANCES,
        'provenance': provenance(),
    }
    out_path = os.path.join(HERE, 'observables.yml')
    with open(out_path, 'w') as f:
        yaml.dump(ref, f, default_flow_style=False, sort_keys=False)
    print(f"wrote {out_path}")


if __name__ == '__main__':
    main()
