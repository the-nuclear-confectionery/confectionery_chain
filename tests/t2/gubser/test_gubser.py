"""T2: CCAKE vs the semi-analytic Viscous Gubser flow WITH CONSERVED CHARGES.

Benchmarks CCAKE's baryon-charge (BSQ) evolution against the analytic
Viscous-Gubser-with-Conserved-Charges (VGCC) solution of

  K. Ingles, J. Salinas San Martin, W. Serenone, J. Noronha-Hostler,
  "Viscous Gubser flow with conserved charges to benchmark fluid
   simulations", arXiv:2503.20021 [nucl-th].

Reference data (the VGCC IC + analytic profiles VGCC_tau=*.dat, EoS2 conformal,
mu/T = 0.3) is NOT vendored (each file is ~9 MB). Point CHAIN_VGCC_DIR at the
analytic-solutions folder of the VGCC repo:
  <vgcc>/data/output/analytic_solutions/EoS2/mu_over_T_0.3
The test skips if the data (or a CCAKE build) is absent.

CCAKE reads the VGCC IC (already in ccake format, with a baryon-density column),
evolves it with the conformal EoS + baryon/strange/electric charges on and
eta/s = 0.2, and the baryon density rhoB(x) and flow u^x(x) along y=0 at
tau = 1.5 and 1.9 fm/c are compared to the analytic profiles.

Runtime scales with dt (reference 0.001 -> ~30 min). Override with
CHAIN_GUBSER_DT for a quicker, coarser check.
"""
import os
import subprocess

import numpy as np
import pytest
import yaml

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CCAKE_DIR = os.path.join(REPO, 'models', 'CCAKE')

VGCC_DIR = os.environ.get(
    'CHAIN_VGCC_DIR',
    '/u/kpala/git_repos/viscous-gubser-with-conserved-charges/'
    'data/output/analytic_solutions/EoS2/mu_over_T_0.3')

DT = float(os.environ.get('CHAIN_GUBSER_DT', '0.001'))
SNAPSHOT_EVERY = 0.1           # fm/c between system_state snapshots
T0 = 1.0                       # IC proper time (fm/c)
TARGETS = [1.5, 1.9]           # compare at these tau (analytic covers 1.0-1.9)

X_WINDOW = 3.0                 # fm — the hot central region
RHOB_FLOOR = 1.0e-3            # 1/fm^3 — compare only where rhoB is meaningful
# At the reference dt=0.001 CCAKE matches the analytic to <1% (measured:
# rhoB max 0.61%, mean 0.33%, u^x max 0.011 at tau=1.9). Tolerances give
# ~2-3x margin so real regressions trip but numerical noise does not.
RHOB_MAX_REL_DEV = 0.02
RHOB_MEAN_REL_DEV = 0.01
UX_MAX_ABS_DEV = 0.03

# ccake IC / analytic column layout (17 cols): x y eta e rhoB rhoS rhoQ ux ...
A_X, A_RHOB, A_UX = 0, 4, 7
# CCAKE system_state column layout (see VGCC plot_Fig4): id t x y eta p T muB
# muS muQ e rhoB ... ux(33)
S_X, S_Y, S_RHOB, S_UX = 2, 3, 11, 33


def _ccake_config(ic_file):
    stride = max(1, int(round(SNAPSHOT_EVERY / DT)))
    return {
        'initial_conditions': {
            'type': 'ccake', 'file': ic_file, 't0': T0, 'dimension': 2,
            'input_as_entropy': False, 'coordinate_system': 'hyperbolic',
        },
        'parameters': {
            'dt': DT, 'h_T': 0.1, 'h_eta': 0.1, 'rk_order': 2,
            'kernel_type': 'cubic_spline', 'energy_cutoff': 0.0,   # keep all particles
            'max_tau': max(TARGETS) + 2 * SNAPSHOT_EVERY,
            'buffer_particles': {'enabled': True, 'circular': True,
                                 'padding_thickness': 0.1},
        },
        # conformal EoS is analytic -> online (on-the-fly) inversion, no table
        'eos': {'type': 'conformal', 'path': 'EoS/Houston',
                'online_inverter_enabled': True},
        'particlization': {'enabled': False, 'type': 'fixed_T', 'T': 150.0},
        'hydro': {
            'baryon_charge_enabled': True,      # the point of this benchmark
            'strange_charge_enabled': True,
            'electric_charge_enabled': True,
            # Mirrors CCAKE's config_visc_gubser.yaml (the known-good VGCC run):
            # 'gubser' shear relaxation (analytic tau_pi) + initial shear from the
            # IC, bulk off, and a (zero-kappa) diffusion block for the charges.
            'viscous_parameters': {
                'shear': {'mode': 'constant', 'constant_eta_over_s': 0.20,
                          'relaxation_mode': 'gubser', 'input_initial_shear': True,
                          'use_vorticity': False, 'delta_pipi_mode': 'default',
                          'tau_pipi_mode': 'disabled', 'lambda_piPi_mode': 'disabled',
                          'phi6_mode': 'disabled', 'phi7_mode': 'disabled'},
                'bulk': {'mode': 'constant', 'constant_zeta_over_s': 0.0,
                         'cs2_dependent_zeta_A': 1.67552, 'cs2_dependent_zeta_p': 2.0,
                         'relaxation_mode': 'default', 'modulate_with_tanh': False,
                         'delta_PiPi_mode': 'israel-stewart', 'lambda_Pipi_mode': 'default',
                         'phi1_mode': 'disabled', 'phi3_mode': 'disabled',
                         'bulk_from_trace': False},
                'diffusion': {'input_initial_diffusion': False,
                              'mode': 'constant_over_T2',
                              'constant_kappa_over_T2': [[0.0, 0.0, 0.0],
                                                         [0.0, 0.0, 0.0],
                                                         [0.0, 0.0, 0.0]],
                              'relaxation_mode': 'constant_over_T'},
            },
        },
        'output': {'print_conservation_state': True, 'hdf_evolution': False,
                   'txt_evolution': True, 'check_causality': False,
                   'evolution_stride': stride},
    }


def _y0(rows, xcol, ycol, cols):
    """(x, *cols) on the y~=0 row, sorted by x."""
    sel = np.abs(rows[:, ycol]) < 0.026        # half the 0.05 fm grid spacing
    r = rows[sel]
    order = np.argsort(r[:, xcol])
    return (r[order, xcol],) + tuple(r[order, c] for c in cols)


@pytest.fixture(scope='module')
def gubser_run(tmp_path_factory):
    ccake = os.path.join(CCAKE_DIR, 'build', 'ccake')
    ic = os.path.join(VGCC_DIR, 'VGCC_initial_condition.dat')
    if not os.path.isfile(ccake):
        pytest.skip("CCAKE not built (./chain rebuild ccake)")
    if not os.path.isfile(ic):
        pytest.skip(f"VGCC reference data not found (set CHAIN_VGCC_DIR); looked in {VGCC_DIR}")

    workdir = tmp_path_factory.mktemp('vgcc')
    config = str(workdir / 'gubser.yaml')
    with open(config, 'w') as f:
        yaml.dump(_ccake_config(ic), f)
    outdir = str(workdir / 'output')
    os.makedirs(outdir, exist_ok=True)
    log_path = str(workdir / 'ccake.log')
    # run from the CCAKE build dir so the conformal EoS relative path resolves
    with open(log_path, 'w') as log:
        proc = subprocess.run([ccake, config, outdir],
                              cwd=os.path.join(CCAKE_DIR, 'build'),
                              stdout=log, stderr=subprocess.STDOUT, timeout=21600)
    assert proc.returncode == 0, f"CCAKE VGCC run failed, see {log_path}"
    return outdir


@pytest.mark.parametrize('tau', TARGETS)
def test_vgcc_baryon_and_flow(gubser_run, tau):
    idx = int(round((tau - T0) / SNAPSHOT_EVERY))
    snap = os.path.join(gubser_run, f'system_state_{idx}.dat')
    assert os.path.isfile(snap), f"no snapshot for tau={tau} (system_state_{idx}.dat)"

    # system_state has trailing string columns (e.g. the EoS name), so read
    # only the numeric columns we need -> [x, y, rhoB, ux].
    sim = np.loadtxt(snap, skiprows=1, usecols=(S_X, S_Y, S_RHOB, S_UX))
    x_sim, rhoB_sim, ux_sim = _y0(sim, 0, 1, (2, 3))

    ref = np.loadtxt(os.path.join(VGCC_DIR, f'VGCC_tau={tau:.2f}.dat'),
                     skiprows=1, usecols=(A_X, 1, A_RHOB, A_UX))
    x_ref, rhoB_ref, ux_ref = _y0(ref, 0, 1, (2, 3))

    sel = (np.abs(x_ref) < X_WINDOW) & (np.abs(rhoB_ref) > RHOB_FLOOR)
    assert sel.sum() > 10, "too few reference points in the comparison window"

    rhoB_i = np.interp(x_ref[sel], x_sim, rhoB_sim)
    rel = np.abs(rhoB_i - rhoB_ref[sel]) / np.abs(rhoB_ref[sel])
    assert rel.max() < RHOB_MAX_REL_DEV, \
        f"tau={tau}: max rhoB rel dev {rel.max():.2%} > {RHOB_MAX_REL_DEV:.0%}"
    assert rel.mean() < RHOB_MEAN_REL_DEV, \
        f"tau={tau}: mean rhoB rel dev {rel.mean():.2%} > {RHOB_MEAN_REL_DEV:.0%}"

    ux_i = np.interp(x_ref[sel], x_sim, ux_sim)
    dev = np.abs(ux_i - ux_ref[sel])
    assert dev.max() < UX_MAX_ABS_DEV, \
        f"tau={tau}: max |u^x| dev {dev.max():.3f} > {UX_MAX_ABS_DEV}"
