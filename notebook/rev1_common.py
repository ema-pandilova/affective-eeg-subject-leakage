"""
Shared definitions for the Frontiers revision analyses (rev1 E1 to E5), on corrected DEAP labels.

Everything a reader needs to reproduce the revised numbers is fixed here: data and labels, the label
threshold, fold construction, the classifier, trial-level aggregation and the resampling scheme.

Labels
    global       threshold = median rating of the TRAINING rows of each fold; label = rating >= threshold.
                 No held-out rating enters the label definition in any protocol.
    participant  each participant's own median over all of their trials (the submission's sensitivity
                 scheme). It is target-derived by construction and is reported only as a sensitivity analysis.
Folds (5-fold unless stated; one seed; no stratification, so no label enters fold assignment)
    P1  KFold on windows, shuffled                  windows of one trial fall on both sides
    P2  GroupKFold on trials, shuffled              participants on both sides, trials disjoint
    P3  GroupKFold on participants, shuffled        participants disjoint
    P4  LeaveOneGroupOut on participants            participants disjoint, one participant per fold
Scoring
    Window probabilities are averaged within each trial; the primary metric is pooled trial-level AUC.
    95% intervals: percentile participant bootstrap (1,000 draws, one shared draw matrix per dataset), so
    differences between protocols or conditions are paired on the same resampled participants.
"""
from __future__ import annotations
import json, platform, sys, time
from pathlib import Path
import numpy as np, pandas as pd
import scipy, sklearn, xgboost
from sklearn.model_selection import KFold, GroupKFold, LeaveOneGroupOut
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier

import run_protocols as R
import deap_labels
from deap_labels import sha256
from rev1_provenance import git_state

SEED = R.SEED
N_BOOT = 1000
OUT = (R.HERE / "../results/rev1").resolve()
XGB_PARAMS = dict(n_estimators=200, max_depth=3, learning_rate=0.1, subsample=0.8, colsample_bytree=0.8,
                  eval_metric="logloss", random_state=SEED, n_jobs=4, verbosity=0)
TARGETS = ["valence", "arousal"]


def xgb():
    return XGBClassifier(**XGB_PARAMS)


def load(name):
    X, val, aro, subj, trial = R.get_data(name)
    if name == "DEAP":
        val, aro = deap_labels.corrected_for_windows(trial, val, aro)
    stim = np.array([int(t.split("_")[1]) for t in trial])   # DEAP: experiment id - 1; DREAMER: film index; FACED: video index - 1
    D = dict(name=name, X=X.astype(float), ratings=dict(valence=np.asarray(val, float), arousal=np.asarray(aro, float)),
             subj=np.asarray(subj), trial=np.asarray(trial), stim=stim)
    if name == "FACED":                                       # presentation block of each window (same-valence blocks of four)
        D["block"] = np.load(R.CACHE / "FACED.npz")["block"]
    return D


def labels(r, tr, scheme, subj):
    if scheme == "global":
        thr = float(np.median(r[tr]))
        return (r >= thr).astype(int), thr
    if scheme == "participant":
        y = np.zeros(len(r), int)
        for s in np.unique(subj):
            m = subj == s
            y[m] = (r[m] >= np.median(r[m])).astype(int)
        return y, None
    raise ValueError(scheme)


def splits(protocol, subj, trial, seed=SEED, block=None):
    idx = np.arange(len(subj))
    if protocol == "P1":
        sp = KFold(5, shuffle=True, random_state=seed).split(idx)
    elif protocol == "P2":
        sp = GroupKFold(5, shuffle=True, random_state=seed).split(idx, groups=trial)
    elif protocol == "P2B":                                   # FACED: whole presentation blocks held out, participants on both sides
        groups = np.array([f"{s}_{b}" for s, b in zip(subj, block)])
        sp = GroupKFold(5, shuffle=True, random_state=seed).split(idx, groups=groups)
    elif protocol == "P3":
        sp = GroupKFold(5, shuffle=True, random_state=seed).split(idx, groups=subj)
    elif protocol == "P4":
        sp = LeaveOneGroupOut().split(idx, groups=subj)
    else:
        raise ValueError(protocol)
    out = []
    for tr, te in sp:
        if protocol in ("P2", "P2B", "P3", "P4"):
            assert not set(trial[tr]) & set(trial[te]), "trial overlap"
        if protocol in ("P3", "P4"):
            assert not set(subj[tr]) & set(subj[te]), "participant overlap"
        out.append((tr, te))
    return out


def rate_by(y_tr, key_tr, key_te, fallback):
    """Training-set positive rate for each key (participant or stimulus); unseen keys get the fallback."""
    rates = pd.Series(y_tr).groupby(key_tr).mean()
    return pd.Series(key_te).map(rates).fillna(fallback).to_numpy(float)


def to_trials(df, score_cols):
    """Average window scores within trial. Labels are constant within a trial in every protocol except P1,
    where a trial's windows can sit in folds with different thresholds; the majority label is used and the
    number of such trials is reported."""
    agg = dict(subj=("subj", "first"), stim=("stim", "first"), y=("y", "mean"), fold=("fold", "min"),
               n_folds=("fold", "nunique"), **{c: (c, "mean") for c in score_cols})
    T = df.groupby("trial", sort=True).agg(**agg).reset_index()
    T["label_mixed"] = (T.y > 0) & (T.y < 1)
    T["y"] = (T.y >= 0.5).astype(int)
    return T


def draws(subjects, n=N_BOOT, seed=SEED):
    """Participant bootstrap as a count matrix (draws x participants)."""
    subjects = np.unique(subjects)
    rng = np.random.default_rng(seed)
    idx = np.stack([rng.choice(len(subjects), len(subjects), replace=True) for _ in range(n)])
    counts = np.stack([np.bincount(row, minlength=len(subjects)) for row in idx])
    return dict(subjects=subjects, counts=counts)


def stim_draws(stimuli, n=N_BOOT, seed=SEED + 1):
    return draws(stimuli, n, seed)


def boot_aucs(y, p, subj, D, stim=None, S=None):
    """AUC under each bootstrap draw, as integer sample weights (identical to duplicating rows).
    With S (a stimulus draw matrix) the weights are crossed: participant count x stimulus count."""
    w_p = D["counts"][:, np.searchsorted(D["subjects"], subj)]
    if S is not None:
        w_p = w_p * S["counts"][:, np.searchsorted(S["subjects"], stim)]
    out = np.full(len(w_p), np.nan)
    for b in range(len(w_p)):
        w = w_p[b]
        m = w > 0
        if len(np.unique(y[m])) == 2:
            out[b] = roc_auc_score(y[m], p[m], sample_weight=w[m])
    return out


def ci(a):
    a = a[~np.isnan(a)]
    return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]


def summarize(y, p, subj, D, stim=None, S=None):
    b = boot_aucs(y, p, subj, D, stim, S)
    return dict(auc=float(roc_auc_score(y, p)), ci=ci(b), n=int(len(y)), n_pos=int(y.sum())), b


def paired(point_a, point_b, boot_a, boot_b):
    return dict(diff=float(point_a - point_b), ci=ci(boot_a - boot_b))


def within_fold_auc(y, p, fold):
    """AUC over positive-negative pairs from the same fold only (null centre 0.5 for fold-constant offsets)."""
    num = den = 0.0
    for f in np.unique(fold):
        m = fold == f
        n1 = int(y[m].sum()); n0 = int(m.sum()) - n1
        if n1 and n0:
            num += roc_auc_score(y[m], p[m]) * n1 * n0; den += n1 * n0
    return float(num / den) if den else float("nan")


def manifest(script, **extra):
    files = ["run_protocols.py", "deap_labels.py", "rev1_provenance.py", "rev1_common.py", script]
    return dict(command=" ".join(sys.argv), written=time.strftime("%Y-%m-%d %H:%M:%S %z"),
                python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                scipy=scipy.__version__, sklearn=sklearn.__version__, xgboost=xgboost.__version__,
                seed=SEED, n_boot=N_BOOT, xgb_params=XGB_PARAMS, git=git_state(),
                script_sha256={f: sha256(R.HERE / f) for f in files},
                inputs_sha256={**{f"cache/{n}.npz": sha256(R.CACHE / f"{n}.npz") for n in ["DEAP", "DREAMER", "FACED"]
                                  if (R.CACHE / f"{n}.npz").exists()},
                               "deap_labels_corrected.csv": sha256(deap_labels.CSV)}, **extra)


def dump(obj, path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
