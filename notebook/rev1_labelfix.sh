#!/usr/bin/env bash
# Frontiers revision (rev1), DEAP label correction: verify labels, reproduce the submission, rerun with
# official labels, build the before/after disclosure, then write results/rev1/PROVENANCE.json tying every
# output to the Git commit it ran from. About 12 minutes on 8 CPU threads.
#
# Refuses to run when a pipeline file differs from HEAD, so definitive outputs always map to a commit.
# ALLOW_DIRTY=1 overrides this for development runs; PROVENANCE.json then records definitive=false.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-../../venv310/bin/python}
export OMP_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1

dirty=$($PY -c 'from rev1_provenance import git_state; print(" ".join(git_state()["dirty_pipeline_files"]))')
if [ -n "$dirty" ] && [ "${ALLOW_DIRTY:-0}" != "1" ]; then
  echo "refusing to run: pipeline files differ from HEAD: $dirty (commit them, or set ALLOW_DIRTY=1)"; exit 2
fi

mkdir -p ../results/rev1
$PY deap_labels.py > ../results/rev1/deap_labels.log
$PY rev1_protocols.py --deap-labels dat --tag gate_dat --gate > ../results/rev1/gate_dat.log 2>&1 & g=$!
$PY rev1_protocols.py --deap-labels corrected --tag corrected > ../results/rev1/corrected.log 2>&1 & c=$!
wait $g || { echo "reproduction gate FAILED, see results/rev1/gate_dat/gate_report.json"; wait $c; exit 1; }
wait $c
$PY rev1_label_diff.py > ../results/rev1/label_diff.log
$PY rev1_provenance.py > ../results/rev1/provenance.log
echo "done: results/rev1/LABEL_CORRECTION.md, results/rev1/PROVENANCE.json"
