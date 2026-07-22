#!/bin/bash
#SBATCH -A bffs-delta-cpu
#SBATCH --partition=cpu
#SBATCH --time=6:30:00
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=1
#SBATCH -J chain_ampt
#SBATCH -o logs/%x_%j.out
#SBATCH -e logs/%x_%j.err
#SBATCH --mem=128G 
set -uo pipefail
mkdir -p logs

# ---- user config ----
PYTHON="${CCAKE_PYTHON:-/u/kpala/.conda/envs/ctop10/bin/python}"
YAML_TEMPLATE="${CCAKE_YAML_TEMPLATE:-test6.yaml}"
DB_FILE="auau4.db"
PYTHON_SCRIPT="wrapper/main.py"

AMPT_OUTPUT_BASE="${CCAKE_AMPT_OUTPUT_BASE:-/work/hdd/bbkr/kpala/paper_holo_noratio_nodiff/holo_noratio_cp1000_19p6}"
OUTPUT_BASE="${CCAKE_OUTPUT_BASE:-/work/hdd/bbkr/kpala/paper_holo_noratio_nodiff/holo_noratio_cp1000_19p6}"

# the template's own tmp base, used to scope + clean up this job's scratch tree
TEMPLATE_TMP_BASE="$("${PYTHON}" scripts/make_event_yaml.py "${YAML_TEMPLATE}" /dev/null)"

# prevent libraries from spawning extra threads
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

LAUNCH_DELAY_SECONDS=0

OK_LIST="logs/ok_${SLURM_JOB_ID}.txt"
FAIL_LIST="logs/fail_${SLURM_JOB_ID}.txt"
: > "${OK_LIST}"
: > "${FAIL_LIST}"

EVT_IDX=0
running=0
for EVT_DIR in "${AMPT_OUTPUT_BASE}"/AMPT_evt*/; do
    echo "DEBUG: found dir: ${EVT_DIR}"
    [ -d "${EVT_DIR}" ] || { echo "DEBUG: not a directory, skipping"; continue; }

    FO_PATH="${EVT_DIR}freeze_out.dat"
    if [ ! -f "${FO_PATH}" ]; then
        echo "WARNING: No freeze_out.dat in ${EVT_DIR}, skipping."
        continue
    fi

    EVT_NAME="$(basename "${EVT_DIR}")"

    # Skip if qvector output already exists
    QVEC_OUT="${OUTPUT_BASE}/q_${EVT_IDX}.root"
    if [ -f "${QVEC_OUT}" ]; then
        echo "SKIP: ${EVT_NAME} (idx=${EVT_IDX}) — qvector already exists: ${QVEC_OUT}"
        (( EVT_IDX++ )) || true
        continue
    fi

    TMP_YAML="test_${EVT_NAME}_${SLURM_JOB_ID}.yaml"

    EVENT_TMP="${TEMPLATE_TMP_BASE}/${SLURM_JOB_ID}/${EVT_NAME}"
    "${PYTHON}" scripts/make_event_yaml.py "${YAML_TEMPLATE}" "${TMP_YAML}" \
        --output "${OUTPUT_BASE}" \
        --tmp "${EVENT_TMP}" \
        --particlization-input-file "${FO_PATH}" \
        > /dev/null

    # per-event logs
    EVT_OUT="logs/${EVT_NAME}_idx${EVT_IDX}_${SLURM_JOB_ID}.out"
    EVT_ERR="logs/${EVT_NAME}_idx${EVT_IDX}_${SLURM_JOB_ID}.err"

    # run each event in a subshell:
    # - it can fail without killing the main script
    # - it appends to OK/FAIL lists
    (
      echo "===== ${EVT_NAME} (idx=${EVT_IDX}) $(date) ====="
      echo "FO_PATH=${FO_PATH}"
      echo "TMP_YAML=${TMP_YAML}"
      echo "DB_FILE=${DB_FILE}"
      echo

      "${PYTHON}" "${PYTHON_SCRIPT}" "${EVT_IDX}" "${DB_FILE}" "${TMP_YAML}"
      rc=$?

      echo
      if [ $rc -eq 0 ]; then
        echo "[OK] ${EVT_NAME} idx=${EVT_IDX}"
        echo "${EVT_NAME} idx=${EVT_IDX}" >> "${OK_LIST}"
      else
        echo "[FAIL] ${EVT_NAME} idx=${EVT_IDX} rc=${rc}"
        echo "${EVT_NAME} idx=${EVT_IDX} rc=${rc}" >> "${FAIL_LIST}"
      fi

      exit $rc
    ) >"${EVT_OUT}" 2>"${EVT_ERR}" &
    (( running++ )) || true

    sleep "${LAUNCH_DELAY_SECONDS}"

    # throttle to SLURM_NTASKS concurrent sruns
    if (( running >= SLURM_NTASKS )); then
        wait -n || true   # don't die if the waited job failed
        (( running-- )) || true
    fi

    (( EVT_IDX++ )) || true
done

# wait for the remaining background jobs (don’t fail the script if some failed)
wait

# keep YAMLs if you want debugging; otherwise remove:
rm -f test_AMPT_evt*_${SLURM_JOB_ID}.yaml

# remove the job-level tmp directory (per-event subdirs already cleaned by main.py)
rm -rf "${TEMPLATE_TMP_BASE}/${SLURM_JOB_ID}"

echo "Done."
echo "OK list:   ${OK_LIST}"
echo "FAIL list: ${FAIL_LIST}"