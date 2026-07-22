#!/bin/bash
# Run the T2 physics validation tier (Gubser check + conservation + fixed-seed
# reference regression) on a Delta compute node. Needs a fully built chain
# (./chain install) in the submitting directory.
#
#   sbatch tests/run_t2.sbatch
#
#SBATCH --account=bbkr-delta-cpu
#SBATCH --partition=cpu
#SBATCH --job-name=chain_t2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH -o logs/t2_%j.out
#SBATCH -e logs/t2_%j.err
set -euo pipefail
mkdir -p logs

cd "${SLURM_SUBMIT_DIR:-$PWD}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

./chain validate t2
