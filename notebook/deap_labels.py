"""
Authoritative DEAP valence/arousal labels for the Frontiers revision (rev1).

The mirror in data/deap/data_preprocessed_python/ carries a 9 - x reflection of both the valence and the
arousal rating on 439 of its 1,280 trials. Its EEG, dominance and liking columns are intact, so the cached
features stay valid and only the two label vectors are replaced.

Source of truth: data/deap/metadata/participant_ratings.xls (the official DEAP ratings file).
data/deap/deap_labels_corrected.csv is the join of that sheet onto the .dat trial order; every
property the join relies on is re-checked here from the raw files rather than trusted:

  1. the CSV equals the official sheet on (participant, experiment id) for all four ratings;
  2. .dat trial index t is experiment id t + 1, proven by dominance and liking matching exactly;
  3. every .dat valence/arousal value is either the official rating or its reflection 9 - x;
  4. an independent clean mirror (data_preprocessed_python_clean/) carries the official ratings on every
     trial and EEG byte-identical to the mirror the features were computed from;
  5. the feature cache's label vectors equal the .dat values, trial by trial.

Usage:
    python deap_labels.py            # run all checks, write results/rev1/deap_label_verification.json
"""
from __future__ import annotations
import os, json, pickle, hashlib
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("QEEG_DATA_ROOT", HERE / "../.."))
CSV = ROOT / "data/deap/deap_labels_corrected.csv"
XLS = ROOT / "data/deap/metadata/participant_ratings.xls"
DAT = ROOT / "data/deap/data_preprocessed_python"
CLEAN = ROOT / "data/deap/data_preprocessed_python_clean"
RATINGS = ["valence", "arousal", "dominance", "liking"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_table():
    C = pd.read_csv(CSV)
    assert len(C) == 1280, len(C)
    assert not C.duplicated(["subject", "dat_trial_index"]).any()
    assert sorted(C.subject.unique()) == list(range(1, 33))
    assert all(sorted(g) == list(range(40)) for _, g in C.groupby("subject").dat_trial_index)
    assert (C.experiment_id == C.dat_trial_index + 1).all()
    for r in RATINGS:
        assert C[r].between(1, 9).all(), r
    return C


def check_against_official(C):
    x = pd.read_excel(XLS).rename(columns=str.lower)
    assert len(x) == 1280
    m = C.merge(x, left_on=["subject", "experiment_id"], right_on=["participant_id", "experiment_id"],
                suffixes=("", "_xls"), validate="one_to_one")
    assert len(m) == 1280
    maxdiff = {r: float(np.abs(m[r] - m[f"{r}_xls"]).max()) for r in RATINGS}
    assert all(v < 1e-9 for v in maxdiff.values()), maxdiff
    return maxdiff


def check_against_dat(C):
    lut = C.set_index(["subject", "dat_trial_index"])
    reflected = {"valence": 0, "arousal": 0}
    for s in range(1, 33):
        lab = pickle.load(open(DAT / f"s{s:02d}.dat", "rb"), encoding="latin1")["labels"]
        assert lab.shape == (40, 4), lab.shape
        for t in range(40):
            row = lut.loc[(s, t)]
            # dominance and liking are intact, so they pin the trial order
            assert lab[t, 2] == row.dominance and lab[t, 3] == row.liking, (s, t)
            for col, r, bad in [(0, "valence", "dat_col0_BAD"), (1, "arousal", "dat_col1_BAD")]:
                assert np.isclose(lab[t, col], row[bad]), (s, t, r)
                same, refl = np.isclose(lab[t, col], row[r]), np.isclose(lab[t, col], 9 - row[r])
                assert same or refl, (s, t, r, lab[t, col], row[r])
                reflected[r] += int(refl and not same)
    return reflected


def check_against_clean_mirror(C):
    """The clean mirror must carry the official ratings, and EEG identical to the mirror the cache was built from."""
    lut = C.set_index(["subject", "dat_trial_index"])
    label_mismatch, eeg_identical = 0, 0
    for s in range(1, 33):
        clean = pickle.load(open(CLEAN / f"s{s:02d}.dat", "rb"), encoding="latin1")
        used = pickle.load(open(DAT / f"s{s:02d}.dat", "rb"), encoding="latin1")
        eeg_identical += int(np.array_equal(clean["data"], used["data"]))
        for t in range(40):
            row = lut.loc[(s, t)]
            label_mismatch += int(not np.allclose(clean["labels"][t], row[RATINGS].to_numpy(float)))
    assert label_mismatch == 0 and eeg_identical == 32, (label_mismatch, eeg_identical)
    return dict(label_mismatches=label_mismatch, participants_with_identical_eeg=eeg_identical)


def corrected_for_windows(trial, val_dat, aro_dat, C=None):
    """Map window-level trial ids ("<subject>_<dat index>") to official valence and arousal.

    val_dat/aro_dat are the cache's .dat-derived vectors; each must equal the CSV's record of the
    .dat value for its trial, which proves the cache and the join refer to the same trials.
    """
    C = load_table() if C is None else C
    key = C.subject.astype(str) + "_" + C.dat_trial_index.astype(str)
    lut = dict(zip(key, C[["valence", "arousal", "dat_col0_BAD", "dat_col1_BAD"]].to_numpy()))
    missing = set(np.unique(trial)) - set(lut)
    assert not missing, sorted(missing)[:5]
    arr = np.stack([lut[t] for t in trial])
    assert np.allclose(arr[:, 2], val_dat) and np.allclose(arr[:, 3], aro_dat), "cache labels do not match .dat"
    return arr[:, 0], arr[:, 1]


if __name__ == "__main__":
    C = load_table()
    from rev1_provenance import git_state
    out = dict(git=git_state(), csv=str(CSV), csv_sha256=sha256(CSV), xls=str(XLS), xls_sha256=sha256(XLS))
    out["max_abs_diff_vs_official"] = check_against_official(C)
    out["reflected_trials_in_dat"] = check_against_dat(C)
    out["clean_mirror"] = check_against_clean_mirror(C)
    either = int(((~np.isclose(C.dat_col0_BAD, C.valence)) | (~np.isclose(C.dat_col1_BAD, C.arousal))).sum())
    out["trials_with_any_reflection"] = either

    z = np.load(HERE / "cache/DEAP.npz", allow_pickle=True)
    val, aro = corrected_for_windows(z["trial"], z["val"], z["aro"], C)
    out["cache"] = dict(sha256=sha256(HERE / "cache/DEAP.npz"), windows=int(len(val)),
                        trials=int(len(np.unique(z["trial"]))),
                        windows_with_changed_valence=int((val != z["val"]).sum()),
                        windows_with_changed_arousal=int((aro != z["aro"]).sum()))
    dest = HERE / "../results/rev1"; dest.mkdir(parents=True, exist_ok=True)
    (dest / "deap_label_verification.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
