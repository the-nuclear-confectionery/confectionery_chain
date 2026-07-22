#!/bin/bash
# Chain submitter — one event per SLURM array task.
#
# Edit the SETTINGS block below, then just run:
#     scripts/submit_array.sh
#
# It submits the array itself (event id = SLURM array index). Check results with:
#     sacct -j <jobid> --format=JobID,State,ExitCode
#
set -uo pipefail

# ============================================================================
#  SETTINGS  —  edit these
# ============================================================================
CONFIG="examples/pbpb_5p02_trento_iccing/config.yml"   # chain config yaml
DB="events.db"                                          # metadata db (SQLite)
CONDA_ENV="ctop10"                                      # conda env to run in

FIRST_EVENT=0                                           # first event id
N_EVENTS=10                                             # number of events
MAX_CONCURRENT=20                                       # array tasks running at once
#Tune below deppending on your cluster and job requirements (energy, modules, etc)
ACCOUNT="bffs-delta-cpu"                                # SLURM account   (sacctmgr show assoc user=$USER)
PARTITION="cpu"                                         # SLURM partition (sinfo -s)
CPUS=1                                                  # cpus per event
MEM="8G"                                                # memory per event
TIME="04:00:00"                                         # walltime per event
# ============================================================================
#  machinery  —  no need to edit below
# ============================================================================
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
cd "$(dirname "$SELF")/.." || exit 1        # repo root
# interpreter: $CONDA_ENV -> its python (override PYTHON directly if elsewhere)
PYTHON="${PYTHON:-$HOME/.conda/envs/${CONDA_ENV}/bin/python}"

# ---- worker: inside an array task -> run that one event ----
if [ -n "${SLURM_ARRAY_TASK_ID:-}" ]; then
    export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-$CPUS}"
    export OMP_PROC_BIND=spread OMP_PLACES=threads
    export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
    ievt="$SLURM_ARRAY_TASK_ID"
    echo "event $ievt | config=$CONFIG | db=$DB | OMP_NUM_THREADS=$OMP_NUM_THREADS | $(date)"
    "$PYTHON" wrapper/main.py "$ievt" "$DB" "$CONFIG"; rc=$?
    echo "event $ievt finished rc=$rc | $(date)"
    exit $rc
fi

# ---- launcher: submit the array ----
[ -f "$CONFIG" ] || { echo "config not found: $CONFIG" >&2; exit 1; }
mkdir -p logs
LAST_EVENT=$(( FIRST_EVENT + N_EVENTS - 1 ))
echo "submitting events ${FIRST_EVENT}..${LAST_EVENT} (<=${MAX_CONCURRENT} at once)"
echo "  config=$CONFIG  db=$DB"
echo "  per event: account=$ACCOUNT partition=$PARTITION cpus=$CPUS mem=$MEM time=$TIME"

sbatch --account="$ACCOUNT" --partition="$PARTITION" --time="$TIME" \
       --nodes=1 --ntasks=1 --cpus-per-task="$CPUS" --mem="$MEM" \
       --job-name=chain_evt --no-requeue \
       --array="${FIRST_EVENT}-${LAST_EVENT}%${MAX_CONCURRENT}" \
       -o "logs/%x_%A_%a.out" -e "logs/%x_%A_%a.err" \
       "$SELF"
