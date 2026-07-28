#!/bin/bash
# Alternative submitter — an event range packed onto ONE node, run N at a time
# with GNU parallel (one allocation instead of a SLURM array).
#
# Edit the SETTINGS block and the #SBATCH resources below, then:
#     mkdir -p logs && sbatch scripts/run_wrapper.sh
#
#SBATCH --account=bffs-delta-cpu
#SBATCH --job-name=chain
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --no-requeue
#SBATCH -t 12:00:00
#SBATCH -o logs/%x_%j.out
#SBATCH -e logs/%x_%j.err
set -uo pipefail

# ============================================================================
#  SETTINGS  —  edit these
# ============================================================================
CONFIG="examples/pbpb_5p02_trento_iccing/config.yml"   # chain config yaml
DB="events.db"                                          # metadata db (SQLite)
CONDA_ENV="ctop10"                                      # conda env to run in

FIRST_EVENT=0                                           # first event id
N_EVENTS=10                                             # number of events
# ============================================================================
#  machinery  —  no need to edit below
# ============================================================================
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1        # repo root
mkdir -p logs
# interpreter: $CONDA_ENV -> its python (override PYTHON directly if elsewhere)
PYTHON="${PYTHON:-$HOME/.conda/envs/${CONDA_ENV}/bin/python}"

LAST_EVENT=$(( FIRST_EVENT + N_EVENTS - 1 ))
NPROC="${SLURM_NTASKS:-$(nproc)}"                      # concurrent workers
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"     # threads per worker
export OMP_PROC_BIND=spread OMP_PLACES=threads
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

JOBID="${SLURM_JOB_ID:-local$$}"
OK="logs/ok_${JOBID}.txt"; FAIL="logs/fail_${JOBID}.txt"; : > "$OK"; : > "$FAIL"
[ -f "$CONFIG" ] || { echo "config not found: $CONFIG" >&2; exit 1; }
command -v parallel >/dev/null || { echo "GNU parallel not found" >&2; exit 1; }
echo "events ${FIRST_EVENT}..${LAST_EVENT}, ${NPROC} concurrent, config=$CONFIG"

run_one() {
    log="logs/event_${1}_${JOBID}.log"
    if "$PYTHON" wrapper/main.py "$1" "$DB" "$CONFIG" > "$log" 2>&1; then
        echo "$1" >> "$OK";   echo "[ok]   event $1"
    else
        echo "$1" >> "$FAIL"; echo "[FAIL] event $1 (see $log)"
    fi
}
export -f run_one; export PYTHON CONFIG DB JOBID OK FAIL

seq "$FIRST_EVENT" "$LAST_EVENT" | parallel -j "$NPROC" run_one {}
echo "done: $(wc -l < "$OK") ok, $(wc -l < "$FAIL") failed"
[ "$(wc -l < "$FAIL")" -eq 0 ]
