"""T2: fixed-seed physics-observable regression.

Restarts each system from its gold-standard CCAKE freeze-out surface, runs
BQSSampler -> SMASH (decays only) -> qvector with fixed seeds, and checks the
resulting charged-particle observables (dNch/deta, <pT>, v2, v3) against the
stored references in references/observables.yml within tolerance.

Skips if the gold surfaces (CHAIN_GOLD_SURFACES_DIR) or a CCAKE-chain build
are absent. Regenerate the references with references/regenerate_observables.py
after an intentional physics change.
"""
import os
import sys

import pytest
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
REPO = os.path.dirname(TESTS)
sys.path.insert(0, TESTS)
sys.path.insert(0, HERE)

from conftest import run_chain_event                    # noqa: E402
from observable_runs import SYSTEMS, build_config, surface_path  # noqa: E402
from flow_observables import compute_flow_observables   # noqa: E402

REF_PATH = os.path.join(HERE, 'references', 'observables.yml')
with open(REF_PATH) as f:
    REF = yaml.safe_load(f)
TOL = REF['tolerances']


def _run(sysname, workdir):
    cfg = build_config(sysname, REPO,
                       os.path.join(str(workdir), 'out'),
                       os.path.join(str(workdir), 'tmp'))
    cfg_path = os.path.join(str(workdir), 'config.yml')
    with open(cfg_path, 'w') as f:
        yaml.dump(cfg, f)
    proc, log = run_chain_event(cfg_path, workdir, timeout=10800)
    assert proc.returncode == 0, f"{sysname} chain failed, see {log}"
    return compute_flow_observables(os.path.join(str(workdir), 'out', 'q_0.root'))


@pytest.mark.parametrize('sysname', sorted(SYSTEMS))
def test_observables_regression(sysname, tmp_path):
    if not os.path.isfile(os.path.join(REPO, 'models', 'CCAKE', 'build', 'ccake')):
        pytest.skip("chain not built")
    if not os.path.isfile(surface_path(sysname)):
        pytest.skip(f"gold surface missing (set CHAIN_GOLD_SURFACES_DIR): {surface_path(sysname)}")

    obs = _run(sysname, tmp_path)
    ref = REF['systems'][sysname]['observables']

    for key, tol in TOL.items():
        got, want = obs[key], ref[key]
        rel = abs(got - want) / abs(want) if want else abs(got - want)
        assert rel < tol, (f"{sysname} {key}: {got:.5g} vs ref {want:.5g} "
                           f"(rel {rel:.2%} > {tol:.0%})")
