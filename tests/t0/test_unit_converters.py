"""T0: golden-file unit tests for the wrapper's pure format converters."""
import os

import pytest

from utils.jet_utils import (dijets_csv_to_ccake_jets, energy_to_gev,
                             write_sample_dijets_config)

HERE = os.path.dirname(os.path.abspath(__file__))
GOLD = os.path.join(HERE, 'golden')
REPO = os.path.dirname(os.path.dirname(HERE))


def _golden(name):
    with open(os.path.join(GOLD, name)) as f:
        return f.read()


def test_dijets_csv_to_ccake_jets(tmp_path):
    out = tmp_path / 'jets.dat'
    n = dijets_csv_to_ccake_jets(os.path.join(GOLD, 'dijets_sample.csv'), str(out))
    assert n == 2
    assert out.read_text() == _golden('jets_expected.dat')


def test_dijets_csv_rejects_empty(tmp_path):
    src = tmp_path / 'empty.csv'
    src.write_text('dijet_id,parton_idx,pid,mass,x_vtx,y_vtx,eta_s,tau,'
                   'p0,p1,p2,p3,pT,phi,y,eta\n')
    with pytest.raises(ValueError):
        dijets_csv_to_ccake_jets(str(src), str(tmp_path / 'out.dat'))


def test_write_sample_dijets_config(tmp_path):
    out = tmp_path / 'sample_dijets.conf'
    write_sample_dijets_config(
        str(out), ampt_dir='/event_0/ampt', vertex_source='binary',
        sqrts_gev=19.6, pt_min=4.0, pt_max=8.0, n_dijets=1,
        csv_file='/event_0/jets/dijets.csv', tau_hydro=1.0)
    assert out.read_text() == _golden('sample_dijets_expected.conf')


def test_energy_to_gev():
    assert energy_to_gev(5.36, 'TeV') == 5360.0
    assert energy_to_gev(200, 'GeV') == 200.0
    assert energy_to_gev(500, 'MeV') == 0.5
    with pytest.raises(ValueError):
        energy_to_gev(1.0, 'PeV')


def test_input_ampt_writer(tmp_path):
    """The 41-line positional input.ampt must be reproduced exactly."""
    from utils.input_file import InputFile
    from specializations.ampt_initial_condition import AmptInitialCondition

    cfg = InputFile(os.path.join(REPO, 'tests', 't1', 'configs', 'auau_tiny.yml')
                    ).get_parameters()
    cfg['global']['output'] = str(tmp_path)

    stage = AmptInitialCondition(cfg, None)
    stage.validate()
    path = stage.create_temp_config(0)
    with open(path) as f:
        assert f.read() == _golden('input_ampt_expected.dat')
