"""T1: tiny-grid smoke runs — every stage of each representative chain must
run and produce its declared outputs. Minutes per chain; requires built
modules (skipped otherwise)."""
import os

import pytest

from conftest import require_built, resolve_config, run_chain_event

HERE = os.path.dirname(os.path.abspath(__file__))

# config -> (modules that must be built, files expected under the output dir)
SMOKE = {
    'auau_tiny.yml': (
        ['ampt', 'amptgenesis', 'ccake', 'bqssampler', 'smash', 'qvector_writter'],
        ['event_0/ampt/ampt.dat',
         'event_0/ampt/binary-collisions.dat',
         'event_0/amptgenesis/ccake_ic.dat',
         'event_0/ccake/freeze_out.dat',
         'q_0.root'],
    ),
    'jets_tiny.yml': (
        ['ampt', 'amptgenesis', 'ccake', 'bqssampler', 'smash',
         'qvector_writter', 'sample_dijets'],
        ['event_0/jets/dijets.csv',
         'event_0/jets/jets.dat',
         'event_0/ccake/freeze_out.dat',
         'q_0.root'],
    ),
    'pbpb_tiny.yml': (
        ['trento', 'iccing', 'ccake', 'bqssampler', 'smash', 'qvector_writter'],
        ['event_0/trento/ccake_ic.dat',
         'event_0/iccing/densities0.dat',
         'event_0/ccake/freeze_out.dat',
         'q_0.root'],
    ),
}


@pytest.mark.parametrize('config_name', sorted(SMOKE), ids=lambda c: c.replace('.yml', ''))
def test_smoke_chain(config_name, tmp_path):
    modules, expected = SMOKE[config_name]
    require_built(*modules)

    config_path, output_dir = resolve_config(
        os.path.join(HERE, 'configs', config_name), tmp_path)
    proc, log_path = run_chain_event(config_path, tmp_path)

    assert proc.returncode == 0, (
        f"chain failed (rc={proc.returncode}); tail of {log_path}:\n"
        + ''.join(open(log_path).readlines()[-40:]))

    missing = [f for f in expected
               if not os.path.exists(os.path.join(output_dir, f))]
    assert not missing, f"missing stage outputs: {missing} (log: {log_path})"

    if config_name == 'jets_tiny.yml':
        jets_file = os.path.join(output_dir, 'event_0', 'jets', 'jets.dat')
        rows = [l for l in open(jets_file) if l.strip() and not l.startswith('#')]
        assert len(rows) == 2, "one sampled dijet must yield exactly two partons"
