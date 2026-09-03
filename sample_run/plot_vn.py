#!/usr/bin/env python3
"""Plot charged-particle INTEGRATED flow v_n vs harmonic n (paper style) — the final
step of the sample reproduce chain (see README section 6).

Reads qvector_analysis  integrated_pid0.dat  (single header + row with keys
vn{EP}_pid0_n<n>) and writes  vn_integrated.png / .pdf : v_n^{EP} for n = 2,3,4,5.

Usage:
    python plot_vn.py [QVECTOR_OUT_DIR]     # default: ./qvector_out
"""
import os, sys, glob
import numpy as np
import matplotlib as mpl; mpl.use("Agg")
import matplotlib.pyplot as plt

OUT = sys.argv[1] if len(sys.argv) > 1 else "qvector_out"
NS  = [2, 3, 4, 5]

hits = glob.glob(os.path.join(OUT, "**", "integrated_pid0.dat"), recursive=True)
if not hits:
    sys.exit(f"ERROR: no 'integrated_pid0.dat' under {OUT} — run qvector_analysis first "
             f"(needs integrated: [\"vn{{EP}}\"] in the config).")
f = hits[0]
hdr = open(f).readline().split()
row = np.loadtxt(f, skiprows=1, ndmin=1)
val = dict(zip(hdr, row))

def get(key):
    return val[key] if key in val else np.nan

vn  = [get(f"vn{{EP}}_pid0_n{n}") for n in NS]

plt.rcParams.update({"font.size": 14, "axes.linewidth": 1.2,
                     "xtick.direction": "in", "ytick.direction": "in",
                     "xtick.top": True, "ytick.right": True})
fig, ax = plt.subplots(figsize=(6.2, 5.2))
ax.plot(NS, vn, "o", ms=12, mfc="none", mec="#1D58A7", mew=2.2, label="this run")
ax.axhline(0, color="k", lw=1)
ax.set_xticks(NS)
ax.set_xlabel(r"$n$"); ax.set_ylabel(r"$v_n^{\mathrm{EP}}$")
ax.set_title(r"Integrated charged-particle flow $v_n^{\mathrm{EP}}$")
ax.set_ylim(bottom=min(0, np.nanmin(vn) * 1.2))
ax.text(0.96, 0.95, r"$0.2\leq p_T\leq3$ GeV" + "\n" + r"$|\eta|<0.5$",
        transform=ax.transAxes, va="top", ha="right", fontsize=11)
ax.text(0.03, 0.05, "CCAKE 2.0 chain\nsample run", transform=ax.transAxes,
        va="bottom", ha="left", fontsize=10, color="#555")
fig.tight_layout()
for ext in ("png", "pdf"):
    fig.savefig(f"vn_integrated.{ext}", dpi=160)
print(f"read: {f}")
print("integrated v_n^EP: " + "  ".join(f"v{n}={v:.4f}" for n, v in zip(NS, vn)))
print("wrote: vn_integrated.png, vn_integrated.pdf")
