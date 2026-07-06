#!/usr/bin/env python3
import argparse
import math
import numpy as np


def parse_trento_cfg(cfg_path: str) -> dict:
    """
    Parse a simple TRENTo-style config:
      key = value
    Ignores blank lines and comments (# ...).
    Keeps last occurrence of a key.
    """
    cfg = {}
    with open(cfg_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # allow inline comments after a '#'
            if "#" in line:
                line = line.split("#", 1)[0].strip()
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip()
            cfg[k] = v
    return cfg


def cfg_get_float(cfg: dict, key: str, default=None) -> float:
    if key not in cfg:
        if default is None:
            raise RuntimeError(f"Missing required key '{key}' in cfg")
        return float(default)
    return float(cfg[key])


def cfg_get_int(cfg: dict, key: str, default=None) -> int:
    if key not in cfg:
        if default is None:
            raise RuntimeError(f"Missing required key '{key}' in cfg")
        return int(default)
    return int(float(cfg[key]))


def read_dense_grid(path: str) -> np.ndarray:
    rows = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append([float(x) for x in line.split()])
    if not rows:
        raise RuntimeError(f"No grid rows found in {path}")
    ncols = len(rows[0])
    for i, r in enumerate(rows):
        if len(r) != ncols:
            raise RuntimeError(f"Non-rectangular grid in {path}: row {i} has {len(r)} cols, expected {ncols}")
    return np.array(rows, dtype=np.float64)


def infer_nsteps_from_cfg(cfg: dict) -> int:
    """
    In TRENTo, grid typically runs from -grid_max to +grid_max with step grid_step.
    Many setups yield nsteps = int(2*grid_max/grid_step) + 1.
    """
    gmax = cfg_get_float(cfg, "grid-max")
    dxy  = cfg_get_float(cfg, "grid-step")
    nsteps = int(round(2.0 * gmax / dxy)) + 1
    return nsteps


def main():
    ap = argparse.ArgumentParser(
        description="Convert dense averaged TRENTo IC (block grid) to TRENTo-like sparse format."
    )
    ap.add_argument("--cfg", required=True, help="TRENTo config file used to generate the events (for grid-step/max).")
    ap.add_argument("--dense", required=True, help="Dense averaged grid file (avg.dat).")
    ap.add_argument("--out", required=True, help="Output sparse file (e.g. icAVG.dat).")
    ap.add_argument("--event-num", type=int, default=0, help="Event number to write in sparse header (default 0).")
    ap.add_argument("--mult", type=float, default=None,
                    help="Multiplicity to put in sparse header. If omitted, uses sum(grid)*dxy*dxy as a proxy.")
    ap.add_argument("--no-header", action="store_true", help="Do not write the sparse header line.")
    ap.add_argument("--eps", type=float, default=0.0,
                    help="Threshold: write only cells with value > eps (default 0).")
    args = ap.parse_args()

    cfg = parse_trento_cfg(args.cfg)
    dxy  = cfg_get_float(cfg, "grid-step")
    gmax = cfg_get_float(cfg, "grid-max")

    grid = read_dense_grid(args.dense)
    ny, nx = grid.shape  # rows, cols

    # Consistency check vs cfg expectation
    nsteps_cfg = infer_nsteps_from_cfg(cfg)
    if nsteps_cfg != nx or nsteps_cfg != ny:
        # Not fatal, but warn with details.
        print(f"WARNING: cfg implies nsteps={nsteps_cfg} (from grid-max/step), "
              f"but dense grid is {ny}x{nx}. Proceeding with dense grid size.")

    # Match TRENTo sparse writer coordinates:
    # xcoor starts at -nsteps*dxy/2, ycoor starts at -nsteps*dxy/2, and y increments inside row loop.
    # NOTE: This is *slightly different* from the common "-(nsteps-1)*dxy/2" convention,
    # but we follow your posted write_sparse_file() exactly.
    x0 = -nx * dxy / 2.0
    y0 = -ny * dxy / 2.0

    # multiplicity in header: your sparse header uses event.multiplicity().
    # For an averaged grid we may not have it, so:
    # - if --mult provided, use it
    # - else approximate proxy = sum(grid) * dxy^2
    mult = args.mult
    if mult is None:
        mult = float(grid.sum() * dxy * dxy)

    with open(args.out, "w") as f:
        if not args.no_header:
            f.write(f"{args.event_num} {dxy} {mult} {x0} {y0}\n")

        # Write (x,y,val) for each cell with val > eps.
        # Your code loops: for each row (x fixed), y runs across columns.
        # That means: row index i -> x = x0 + i*dxy
        #             col index j -> y = y0 + j*dxy
        for i in range(ny):
            x = x0 + i * dxy
            for j in range(nx):
                val = grid[i, j]
                if val > args.eps:
                    y = y0 + j * dxy
                    f.write(f"{x} {y} {val}\n")

    print(f"Wrote sparse file: {args.out}")
    print(f"dxy={dxy}, grid={ny}x{nx}, header_mult={mult}, threshold eps={args.eps}")


if __name__ == "__main__":
    main()
