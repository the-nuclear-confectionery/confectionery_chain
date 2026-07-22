"""T2: conserved charges must stay conserved and entropy must not decrease
during the CCAKE evolution of a real (tiny) AMPT event.

CCAKE writes conservation.dat (columns: t Eloss S Btotal Stotal Qtotal) when
output.print_conservation_state is on — auau_tiny has it enabled.
"""
import os

import pytest

from conftest import require_built, resolve_config, run_chain_event

T1_CONFIGS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          't1', 'configs')

ENTROPY_TOL = 5e-3     # allowed fractional entropy *decrease* (numerics)
CHARGE_REL_TOL = 0.02  # allowed relative drift of B and Q totals
CHARGE_ABS_FLOOR = 0.5 # absolute drift floor for small totals


@pytest.fixture(scope='module')
def conservation_data(tmp_path_factory):
    require_built('ampt', 'amptgenesis', 'ccake', 'bqssampler', 'smash', 'qvector_writter')
    workdir = tmp_path_factory.mktemp('conservation')
    config_path, output_dir = resolve_config(
        os.path.join(T1_CONFIGS, 'auau_tiny.yml'), workdir)
    proc, log_path = run_chain_event(config_path, workdir)
    assert proc.returncode == 0, f"chain failed, see {log_path}"

    path = os.path.join(output_dir, 'event_0', 'ccake', 'conservation.dat')
    assert os.path.isfile(path), f"conservation.dat not written to {path}"
    rows = []
    with open(path) as f:
        header = f.readline().split()
        for line in f:
            rows.append([float(x) for x in line.split()])
    assert header == ['t', 'Eloss', 'S', 'Btotal', 'Stotal', 'Qtotal']
    assert len(rows) >= 2, "need at least two conservation samples"
    return rows


def test_entropy_never_decreases(conservation_data):
    entropy = [r[2] for r in conservation_data]
    floor = entropy[0] * (1.0 - ENTROPY_TOL)
    assert min(entropy) >= floor, (
        f"entropy dropped below tolerance: min {min(entropy):.6g} vs initial {entropy[0]:.6g}")
    assert entropy[-1] >= entropy[0] * (1.0 - ENTROPY_TOL)


@pytest.mark.parametrize('column,name', [(3, 'Btotal'), (5, 'Qtotal')])
def test_charge_conservation(conservation_data, column, name):
    values = [r[column] for r in conservation_data]
    drift = abs(values[-1] - values[0])
    allowed = max(CHARGE_REL_TOL * abs(values[0]), CHARGE_ABS_FLOOR)
    assert drift <= allowed, (
        f"{name} drifted by {drift:.4g} (initial {values[0]:.4g}, allowed {allowed:.4g})")
