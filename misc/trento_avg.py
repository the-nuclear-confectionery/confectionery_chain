#!/usr/bin/env python3
import argparse
import os
import glob
import numpy as np

def read_dense_trento_grid(path: str) -> np.ndarray:
    """Read a dense TRENTo IC file (optional # header + full 2D grid)."""
    rows = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line[0] == "#":
                continue
            # dense grid row: space-separated floats
            rows.append([float(x) for x in line.split()])
    if not rows:
        raise RuntimeError(f"No grid data found in {path}")
    # ensure rectangular
    ncols = len(rows[0])
    for i, r in enumerate(rows):
        if len(r) != ncols:
            raise RuntimeError(
                f"Non-rectangular grid in {path}: row {i} has {len(r)} cols, expected {ncols}"
            )
    return np.array(rows, dtype=np.float64)

def gather_files(input_path: str):
    """Return list of .dat files from a directory, a list file, or a single file."""
    if os.path.isdir(input_path):
        files = sorted(glob.glob(os.path.join(input_path, "*.dat")))
        if not files:
            raise RuntimeError(f"No .dat files found in directory: {input_path}")
        return files

    if os.path.isfile(input_path):
        # If it's a .dat, treat as single file. Otherwise treat as a list file.
        if input_path.lower().endswith(".dat"):
            return [input_path]
        else:
            files = []
            with open(input_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    files.append(line)
            if not files:
                raise RuntimeError(f"No paths found in list file: {input_path}")
            return files

    raise RuntimeError(f"Input path not found: {input_path}")

def write_dense_grid(path: str, grid: np.ndarray, header: str | None = None):
    with open(path, "w") as f:
        if header:
            for hline in header.splitlines():
                f.write(f"# {hline}\n")
        for row in grid:
            f.write(" ".join(f"{x:.16g}" for x in row) + "\n")

def main():
    ap = argparse.ArgumentParser(
        description="Average dense TRENTo IC grids (cell-by-cell mean) across many events."
    )
    ap.add_argument("-i", "--input", required=True,
                    help="Directory with *.dat, OR a .txt listing files, OR a single .dat")
    ap.add_argument("-o", "--output", required=True,
                    help="Output averaged grid file (dense format).")
    ap.add_argument("--start", type=int, default=None,
                    help="Optional start index in the file list (after sorting).")
    ap.add_argument("--end", type=int, default=None,
                    help="Optional end index (exclusive) in the file list (after sorting).")
    args = ap.parse_args()

    files = gather_files(args.input)

    # optional slicing
    s = args.start if args.start is not None else 0
    e = args.end if args.end is not None else len(files)
    files = files[s:e]
    if not files:
        raise RuntimeError("No files selected after applying start/end.")

    # accumulate
    sum_grid = None
    n = 0

    for fp in files:
        g = read_dense_trento_grid(fp)
        if sum_grid is None:
            sum_grid = np.zeros_like(g, dtype=np.float64)
            ref_shape = g.shape
        else:
            if g.shape != ref_shape:
                raise RuntimeError(f"Grid shape mismatch: {fp} has {g.shape}, expected {ref_shape}")
        sum_grid += g
        n += 1

    avg_grid = sum_grid / float(n)
    header = f"averaged over {n} events"
    write_dense_grid(args.output, avg_grid, header=header)

    print(f"Wrote averaged grid to: {args.output}")
    print(f"Used {n} files")
    print(f"Grid shape: {avg_grid.shape[0]} x {avg_grid.shape[1]}")

if __name__ == "__main__":
    main()
