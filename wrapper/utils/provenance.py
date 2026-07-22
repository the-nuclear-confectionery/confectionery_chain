"""Per-event provenance: exactly which code and config produced a result.

Records the test_chain commit, every submodule's commit (via `git describe`,
which flags local modifications with a `-dirty` suffix), the fully-defaulted
resolved config, and basic run metadata. Written once per event next to its
copied config so results remain traceable long after `./chain update`.
"""
import datetime
import os
import socket
import subprocess

import yaml


def _describe(path):
    try:
        return subprocess.run(
            ['git', 'describe', '--always', '--dirty', '--long'],
            cwd=path, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def collect_submodule_versions(basedir):
    """{submodule path: git-describe string} for every submodule, plus the
    top-level test_chain repo under the key '.'."""
    versions = {'.': _describe(basedir)}
    try:
        out = subprocess.run(['git', 'submodule', 'status', '--recursive'],
                             cwd=basedir, capture_output=True, text=True,
                             check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return versions
    for line in out.strip().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            path = parts[1]
            versions[path] = _describe(os.path.join(basedir, path))
    return versions


def collect_seeds(config, _prefix=''):
    """{dotted.path: value} for every config key whose name contains 'seed'.

    Seeds are set on scattered per-stage parameter dicts (hijing_seed,
    parton_cascade_seed, sampler seeds, ...); walking the resolved config is
    simpler than threading them through every specialization.
    """
    seeds = {}
    if isinstance(config, dict):
        for key, value in config.items():
            path = f"{_prefix}.{key}" if _prefix else key
            if isinstance(value, (dict, list)):
                seeds.update(collect_seeds(value, path))
            elif 'seed' in key.lower():
                seeds[path] = value
    elif isinstance(config, list):
        for i, value in enumerate(config):
            seeds.update(collect_seeds(value, f"{_prefix}[{i}]"))
    return seeds


def write_provenance(path, config, event_id):
    """Write provenance.yml at `path`. Returns the dict that was written."""
    record = {
        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
        'host': socket.gethostname(),
        'event_id': event_id,
        'seeds': collect_seeds(config['input']),
        'submodule_versions': collect_submodule_versions(config['global']['basedir']),
        'resolved_config': config,
    }
    with open(path, 'w') as f:
        yaml.dump(record, f, default_flow_style=False, sort_keys=False)
    return record
