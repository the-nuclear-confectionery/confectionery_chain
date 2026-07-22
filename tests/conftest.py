"""Shared fixtures/helpers for the chain validation suite.

Tiers:
  t0 — schema + unit tests, seconds, no built modules needed
  t1 — tiny-grid smoke runs of representative chains, minutes, needs builds
  t2 — physics validation (Gubser, conservation, reference observables), long
"""
import os
import subprocess
import sys

import pytest
import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'wrapper'))

# Artifacts proving a module is built (mirrors ./chain's registry).
MODULE_EXE = {
    'ampt': 'models/AMPT/ampt',
    'trento': 'models/trento/build/src/trento',
    'iccing': 'models/ICCING/iccing',
    'amptgenesis': 'models/AMPTGenesis/build/AMPT-Genesis.exe',
    'ccake': 'models/CCAKE/build/ccake',
    'is3d': 'models/iS3D/iS3D',
    'bqssampler': 'models/BQSSampler/build/particlizer',
    'smash': os.path.join(os.environ.get('CONDA_PREFIX', '/nonexistent'), 'bin', 'smash'),
    'qvector_writter': 'models/qvector_writter/build/qvector_writter.exe',
    'sample_dijets': 'utils/sample_dijets/sample_dijets',
}


@pytest.fixture(scope='session')
def repo_root():
    return REPO


def require_built(*modules):
    """Skip the calling test if any required executable is missing."""
    missing = []
    for m in modules:
        path = MODULE_EXE[m]
        if not os.path.isabs(path):
            path = os.path.join(REPO, path)
        if not os.path.exists(path):
            missing.append(m)
    if missing:
        pytest.skip(f"required modules not built: {', '.join(missing)} "
                    f"(run './chain install' or './chain rebuild <module>')")


def deep_update(base, overrides):
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_update(base[k], v)
        else:
            base[k] = v
    return base


def resolve_config(template_path, workdir, overrides=None):
    """Fill __OUTPUT__/__TMP__/__BASEDIR__ placeholders in a test config.

    Returns (config_path, output_dir). workdir is a per-test scratch dir.
    """
    output_dir = os.path.join(str(workdir), 'results')
    tmp_dir = os.path.join(str(workdir), 'tmp')
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(tmp_dir, exist_ok=True)

    with open(template_path) as f:
        text = f.read()
    text = (text.replace('__OUTPUT__', output_dir)
                .replace('__TMP__', tmp_dir)
                .replace('__BASEDIR__', REPO))
    cfg = yaml.safe_load(text)
    if overrides:
        deep_update(cfg, overrides)

    config_path = os.path.join(str(workdir), 'config.yml')
    with open(config_path, 'w') as f:
        yaml.dump(cfg, f, default_flow_style=False)
    return config_path, output_dir


def run_chain_event(config_path, workdir, event_id=0, timeout=5400):
    """Run one event through wrapper/main.py; returns the CompletedProcess.

    stdout/stderr are captured to <workdir>/chain.log for post-mortem. Caps
    BLAS/OpenMP threading to 1 — several modules (e.g. ICCING) size their
    thread pool off the host's core count, which oversubscribes when many
    single-event smoke tests run back to back. submit_chain_ampt.sh applies
    the same cap in production for the same reason (many single-core SLURM
    tasks sharing a node).
    """
    db_path = os.path.join(str(workdir), 'validation.db')
    log_path = os.path.join(str(workdir), 'chain.log')
    # Inherit the caller's thread settings (e.g. OMP_NUM_THREADS exported on a
    # compute node); only cap to 1 when unset, so a bare/constrained shell
    # doesn't oversubscribe and trip thread-creation limits.
    env = dict(os.environ)
    for _var in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        env.setdefault(_var, '1')
    with open(log_path, 'w') as log:
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, 'wrapper', 'main.py'),
             str(event_id), db_path, config_path],
            cwd=REPO, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, env=env)
    return proc, log_path
