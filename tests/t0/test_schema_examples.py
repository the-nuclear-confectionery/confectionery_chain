"""T0: every shipped configuration must validate against the wrapper schema."""
import glob
import os

import pytest

from utils.input_file import InputFile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONFIGS = sorted(
    glob.glob(os.path.join(REPO, 'examples', '*', 'config.yml'))
    + glob.glob(os.path.join(REPO, 'tests', 't1', 'configs', '*.yml'))
    + glob.glob(os.path.join(REPO, 'configs', 'all_options', '*.yaml'))
)


def test_configs_found():
    assert len(CONFIGS) >= 5, f"expected curated examples + t1 configs, found: {CONFIGS}"


@pytest.mark.parametrize('path', CONFIGS, ids=lambda p: os.path.relpath(p, REPO))
def test_config_validates(path):
    cfg = InputFile(path).get_parameters()
    # a validated config always carries the global section fully defaulted
    assert 'grid' in cfg['global'] and 'energy' in cfg['global']
