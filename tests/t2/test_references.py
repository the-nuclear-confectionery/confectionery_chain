"""T2: fixed-seed observable regression against stored references.

References live in tests/t2/references/*.yml (regenerate with
regenerate_references.py after intentional physics changes). Each carries the
submodule SHAs that produced it; observables outside tolerance mean the
chain's physics output changed.
"""
import os

import pytest
import yaml

from conftest import require_built, resolve_config, run_chain_event
from observables import compute_observables

HERE = os.path.dirname(os.path.abspath(__file__))
REF_PATH = os.path.join(HERE, 'references', 'auau_tiny.yml')
T1_CONFIGS = os.path.join(os.path.dirname(HERE), 't1', 'configs')


@pytest.fixture(scope='module')
def reference():
    if not os.path.isfile(REF_PATH):
        pytest.skip("no stored reference — generate one with "
                    "tests/t2/references/regenerate_references.py")
    with open(REF_PATH) as f:
        return yaml.safe_load(f)


def test_reference_observables(reference, tmp_path):
    require_built('ampt', 'amptgenesis', 'ccake', 'bqssampler', 'smash',
                  'qvector_writter')

    config_path, output_dir = resolve_config(
        os.path.join(T1_CONFIGS, reference['config'].split('/')[-1]), tmp_path)
    proc, log_path = run_chain_event(config_path, tmp_path, timeout=7200)
    assert proc.returncode == 0, f"chain failed, see {log_path}"

    observed = compute_observables(output_dir)
    expected = reference['observables']
    tolerances = reference['tolerances']

    failures = []
    for name, ref_value in expected.items():
        tol = tolerances.get(name, 0.05)
        got = observed[name]
        allowed = abs(ref_value) * tol
        if abs(got - ref_value) > allowed:
            failures.append(f"{name}: got {got:.6g}, reference {ref_value:.6g} "
                            f"(tolerance ±{tol:.0%})")
    assert not failures, (
        "observables drifted from the stored reference "
        f"(produced with {reference['provenance']}):\n  " + "\n  ".join(failures))
