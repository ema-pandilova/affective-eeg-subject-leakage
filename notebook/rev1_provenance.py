"""
Provenance for the Frontiers revision (rev1) outputs.

git_state() reports the commit the pipeline runs from and whether any pipeline file differs from it.
Run as a script (the last step of rev1_labelfix.sh) it writes results/rev1/PROVENANCE.json, which ties
every definitive output to that commit and to the exact data files it read.
"""
from __future__ import annotations
import json, subprocess, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
PIPELINE_FILES = ["notebook/run_protocols.py", "notebook/deap_labels.py", "notebook/rev1_protocols.py",
                  "notebook/rev1_label_diff.py", "notebook/rev1_provenance.py", "notebook/rev1_labelfix.sh"]


def _git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args], text=True).strip()


def git_state():
    dirty = [line[3:] for line in _git("status", "--porcelain", "--", *PIPELINE_FILES).splitlines()]
    return dict(commit=_git("rev-parse", "HEAD"), branch=_git("rev-parse", "--abbrev-ref", "HEAD"),
                pipeline_files=PIPELINE_FILES, pipeline_files_clean=not dirty, dirty_pipeline_files=dirty)


if __name__ == "__main__":
    from deap_labels import sha256, CSV, XLS
    rev1 = REPO / "results/rev1"
    state = git_state()
    outputs = ["deap_label_verification.json", "gate_dat/protocols.json", "gate_dat/gate_report.json",
               "corrected/protocols.json", "label_correction_diff.json", "LABEL_CORRECTION.md"]
    recorded = {
        "deap_label_verification.json": json.loads((rev1 / outputs[0]).read_text())["git"]["commit"],
        "gate_dat/protocols.json": json.loads((rev1 / outputs[1]).read_text())["_manifest"]["git"]["commit"],
        "corrected/protocols.json": json.loads((rev1 / outputs[3]).read_text())["_manifest"]["git"]["commit"],
        "label_correction_diff.json": json.loads((rev1 / outputs[4]).read_text())["git"]["commit"],
    }
    assert set(recorded.values()) == {state["commit"]}, f"outputs come from different commits: {recorded}"
    gate = json.loads((rev1 / "gate_dat/gate_report.json").read_text())
    prov = dict(
        written=datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        git=state, commit_recorded_by_each_output=recorded,
        definitive=state["pipeline_files_clean"] and gate["passed"],
        reproduction_gate=dict(passed=gate["passed"], n_values_compared=gate["n_values_compared"],
                               n_differences=gate["n_differences"]),
        inputs_sha256={"notebook/cache/DEAP.npz": sha256(HERE / "cache/DEAP.npz"),
                       "notebook/cache/DREAMER.npz": sha256(HERE / "cache/DREAMER.npz"),
                       "data/deap/deap_labels_corrected.csv": sha256(CSV),
                       "data/deap/metadata/participant_ratings.xls": sha256(XLS)},
        outputs_sha256={o: sha256(rev1 / o) for o in outputs},
        not_versioned="OOF .npz files, bootstrap draw .npy files and logs stay local (ignored by git).")
    (rev1 / "PROVENANCE.json").write_text(json.dumps(prov, indent=2))
    print(json.dumps(prov, indent=2))
