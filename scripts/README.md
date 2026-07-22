# Submission scripts

Batch helpers for running the chain (`wrapper/main.py`) on SLURM (Delta).
**Open the script, edit the `SETTINGS` block at the top, then run it** — no
flags or environment variables to remember.

> **Before the first submit:** `mkdir -p logs` (SLURM evaluates `-o logs/...`
> at submit time and won't create the directory). `logs/` is gitignored.

| Script | Use it for | Run it with |
|---|---|---|
| **`submit_array.sh`** | **Default.** Any number of events, one per SLURM array task (SLURM schedules/retries each independently). | `scripts/submit_array.sh` |
| `submit_chain_ampt.sh` (repo root) | **Restart from an existing freeze-out surface** — particlization → afterburner → analysis over a directory of `freeze_out.dat`s, without re-running IC/hydro. | `sbatch submit_chain_ampt.sh` |
| `make_event_yaml.py` | Templating helper — clone a config and override `output`/`tmp`/particlization `input_file` per event (parse+dump, not `sed`). Used by `submit_chain_ampt.sh`. | — |

## Usage

`submit_array.sh` is the default. Its `SETTINGS` block:

```sh
CONFIG="examples/pbpb_5p02_trento_iccing/config.yml"   # chain config yaml
DB="events.db"                                          # metadata db
CONDA_ENV="ctop10"                                      # conda env -> its python
FIRST_EVENT=0                                           # first event id
N_EVENTS=10                                             # number of events
MAX_CONCURRENT=20                                       # array tasks at once
ACCOUNT="bffs-delta-cpu"; PARTITION="cpu"              # SLURM account / partition
CPUS=1; MEM="8G"; TIME="04:00:00"                     # resources per event
```

The interpreter defaults to `~/.conda/envs/$CONDA_ENV/bin/python` — change
`CONDA_ENV`, or set `PYTHON` directly if your env lives elsewhere. One event
runs on **one CPU** by default (throughput comes from many array tasks, not
threads); bump `CPUS` only for a genuinely multi-threaded CCAKE grid.

Edit those, then:

```sh
mkdir -p logs
scripts/submit_array.sh                    # run directly — it submits the array itself

sacct -j <jobid> --format=JobID,State,ExitCode   # which events failed
```

## Thread environment (baked in)

Every script exports `OMP_NUM_THREADS` (CCAKE/Kokkos) with `OMP_PROC_BIND=spread`
/ `OMP_PLACES=threads`, **and pins `OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=`
`NUMEXPR_NUM_THREADS=1`**. The BLAS/numpy pins matter: without them, numpy-heavy
stages (e.g. ICCING) oversubscribe and OpenBLAS thread-init can abort the job.
