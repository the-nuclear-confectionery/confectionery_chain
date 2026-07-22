"""Shared setup for the T2 physics-observable regression (test_observables.py
and references/regenerate_observables.py).

Each system restarts from a fixed gold-standard CCAKE freeze-out surface and
runs particlization (BQSSampler) -> SMASH (decays only) -> qvector, with fixed
seeds so the observables are reproducible. The surfaces are large physics data
(not vendored); point CHAIN_GOLD_SURFACES_DIR at the directory holding
auau_freeze_out.dat and pbpb_freeze_out.dat.
"""
import os

GOLD_DIR = os.environ.get('CHAIN_GOLD_SURFACES_DIR',
                          '/work/hdd/bffs/kpala/gold_surfaces')

# Fixed seeds -> reproducible sampling/decays.
BQS_SEED = 20260717
SMASH_SEED = 424242

SYSTEMS = {
    'auau_19p6_ampt': dict(
        energy=19.6, unit='GeV', ion='Au', dim=3, step_eta=0.2,
        surface='auau_freeze_out.dat', samples=500, muS=False, muQ=False),
    'pbpb_5p02_trento_iccing': dict(
        energy=5.02, unit='TeV', ion='Pb', dim=2, step_eta=0.0,
        surface='pbpb_freeze_out.dat', samples=100, muS=True, muQ=True),
}


def surface_path(sysname):
    return os.path.join(GOLD_DIR, SYSTEMS[sysname]['surface'])


def build_config(sysname, basedir, output, tmp):
    """Restart-from-surface chain config (IC/overlay/hydro skipped)."""
    s = SYSTEMS[sysname]
    return {
        'global': {
            'output': output, 'tmp': tmp, 'basedir': basedir, 'nevents': 1,
            'grid': {'x_max': 14.0, 'y_max': 14.0, 'eta_max': 6.0,
                     'step_x': 0.2, 'step_y': 0.2, 'step_eta': s['step_eta']},
            'energy': {'value': s['energy'], 'unit': s['unit']},
            'tau_hydro': 1.0, 'ion_A': s['ion'], 'ion_B': s['ion'],
        },
        'input': {
            'particlization': {'type': 'BQSSampler', 'parameters': {
                'input_file': surface_path(sysname), 'mode': 'ccakev2',
                'coordinate_system': 'hyperbolic', 'dimension': s['dim'],
                'use_muB': True, 'use_muS': s['muS'], 'use_muQ': s['muQ'],
                'samples': s['samples'], 'sampling_method': 'regular',
                'delta_f_shear': True, 'delta_f_bulk': True,
                'normalize_deltaf': True, 'y_max': 5.0, 'eos_column': True,
                'seed': BQS_SEED}},
            'afterburner': {'type': 'smash', 'parameters': {
                'decays_only': True,
                'General': {'seed': SMASH_SEED}}},
            'analysis': {'type': 'qvector_writter', 'parameters': {
                'n_max': 6, 'calculate_charged': True,
                'pids': [-211, 211, 321, -321, 2212, -2212, 3122, -3122,
                         3222, 3112, 3334],
                'pt_bins': 120, 'max_pt': 6.0, 'eta_bins': 108, 'max_eta': 5.4,
                'input_type': 'smash_hepmc3', 'output_type': 'root'}},
        },
    }
