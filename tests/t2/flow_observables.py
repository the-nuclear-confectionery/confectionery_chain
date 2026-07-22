"""Physics observables from a qvector_writter q_*.root file (TH2D Q-vectors,
eta x pt, per PID and harmonic). Charged = pi/K/p and antiparticles.

Per (oversampled) event:
  dNch/deta at midrapidity, mean pT (charged, mid-eta), and integrated
  event-plane v2 / v3 (|Q_n| / Q_0 over the mid-eta acceptance).
"""
import numpy as np
import uproot

CHARGED = [211, -211, 321, -321, 2212, -2212]
ETA_MID = 0.5   # |eta| window for midrapidity observables


def compute_flow_observables(q_root_path):
    f = uproot.open(q_root_path)
    nsamp = float(f['hSampleCounter'].to_numpy()[0][0]) if 'hSampleCounter' in [k.split(';')[0] for k in f.keys()] else 1.0

    # geometry from any n0 histogram
    _, eta_edges, pt_edges = f[f'ReQ_pid-211_n0'].to_numpy()
    eta_c = 0.5 * (eta_edges[:-1] + eta_edges[1:])
    pt_c = 0.5 * (pt_edges[:-1] + pt_edges[1:])
    deta = eta_edges[1] - eta_edges[0]
    mid = np.abs(eta_c) < ETA_MID

    def stack(prefix, n):
        tot = None
        for pid in CHARGED:
            key = f'{prefix}_pid{pid}_n{n}'
            if key in [k.split(';')[0] for k in f.keys()]:
                v, _, _ = f[key].to_numpy()
                tot = v if tot is None else tot + v
        return tot  # [eta, pt]

    N = stack('ReQ', 0)                       # multiplicity per (eta,pt)
    # dNch/deta at midrapidity (per real event)
    dN_deta = N.sum(axis=1) / nsamp / deta
    dNch_deta_mid = float(dN_deta[mid].mean())
    # mean pT over charged at mid-eta
    Nmid = N[mid, :].sum(axis=0)              # per pt bin
    mean_pt = float((pt_c * Nmid).sum() / Nmid.sum())

    obs = {'nsamples': nsamp,
           'dNch_deta_mid': dNch_deta_mid,
           'mean_pt_charged': mean_pt}
    # integrated event-plane v_n over mid-eta acceptance
    Q0 = N[mid, :].sum()
    for n in (2, 3):
        Re = stack('ReQ', n)[mid, :].sum()
        Im = stack('ImQ', n)[mid, :].sum()
        obs[f'v{n}'] = float(np.hypot(Re, Im) / Q0)
    return obs


if __name__ == '__main__':
    import sys, json
    print(json.dumps(compute_flow_observables(sys.argv[1]), indent=2))
