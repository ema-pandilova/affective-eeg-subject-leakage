"""
E4 (Frontiers revision): normalization-scope ablation under leave-one-participant-out evaluation (P4).

Every arm uses the same folds, the same training-only label threshold, the same classifier settings and the
same scored rows. A calibration slice of each participant's trials (DEAP 8 of 40, DREAMER 4 of 18, drawn at
random per participant with a fixed seed, before and independent of any label) is removed from training and
from scoring in every arm; it is used only as normalization data in arm B.

Arms (feature-level z-scoring; statistics are per-feature mean and SD)
    none   no normalization (reference)
    A      train-only global: statistics from the training participants' rows
    D      global over all rows, including the held-out participant's scored trials         TRANSDUCTIVE
    B      per participant, from that participant's own unlabelled calibration trials       uses target-participant
                                                                                            data, not scored data
    C      per participant, from that participant's whole recording, scored trials included TRANSDUCTIVE
Training participants are normalized by the same rule as the held-out participant in each arm.
No arm uses any label for normalization.

Raw-signal normalization is not a separate arm: relative band powers, band ratios, Hjorth mobility and
complexity and permutation entropy are invariant to a positive affine rescaling of the signal, so per-recording
signal z-scoring changes only the six Hjorth-activity features. check_affine_invariance() verifies this on DEAP.

Also reported: subject-identity decodability after each normalization (label-free).

    python rev1_e4_normalization.py --dataset DEAP --target valence [--identity-check]
"""
from __future__ import annotations
import argparse, pickle, time
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier
import rev1_common as C
import run_protocols as R

N_CALIB = {"DEAP": 8, "DREAMER": 4}
ARMS = ["none", "A", "D", "B", "C"]
LEAKAGE = {"none": "none", "A": "none (training data only)",
           "D": "transductive: uses the held-out participant's scored feature data (no labels)",
           "B": "uses the held-out participant's unlabelled calibration trials, not the scored trials",
           "C": "transductive: uses the held-out participant's scored feature data (no labels)"}
LEARNERS = ["xgb", "logreg"]


def calibration_mask(subj, trial, n_calib, seed=C.SEED):
    rng = np.random.default_rng(seed); calib = set()
    for s in np.unique(subj):
        ts = np.unique(trial[subj == s])
        calib.update(rng.choice(ts, n_calib, replace=False).tolist())
    return np.isin(trial, list(calib))


def zscore(X, rows_stats):
    mu = X[rows_stats].mean(0); sd = X[rows_stats].std(0) + 1e-12
    return (X - mu) / sd


def per_participant(X, subj, stats_mask):
    Z = np.empty_like(X)
    for s in np.unique(subj):
        m = subj == s
        Z[m] = zscore(X[m], stats_mask[m])
    return Z


def normalize(arm, X, subj, tr, te, calib):
    """Returns normalized features for all rows (only tr and te rows are used downstream)."""
    scored = ~calib
    if arm == "none":
        return X
    if arm == "A":
        m = np.zeros(len(X), bool); m[tr] = True
        return zscore(X, m)
    if arm == "D":
        m = np.zeros(len(X), bool); m[tr] = True; m[te] = True
        return zscore(X, m)
    if arm == "B":
        return per_participant(X, subj, calib)
    if arm == "C":
        return per_participant(X, subj, np.ones(len(X), bool))
    raise ValueError(arm)


def fit_predict(learner, Xtr, ytr, Xte):
    if learner == "xgb":
        return C.xgb().fit(Xtr, ytr).predict_proba(Xte)[:, 1]
    return LogisticRegression(max_iter=5000).fit(Xtr, ytr).predict_proba(Xte)[:, 1]


def check_affine_invariance():
    dd = pickle.load(open(R.DEAP_DIR.parent / "data_preprocessed_python_clean/s01.dat", "rb"), encoding="latin1")
    idx = [R.DEAP_IDX[c] for c in R.CH]
    seg = dd["data"][0, idx, R.BASELINE_S * R.FS:R.BASELINE_S * R.FS + R.WIN_S * R.FS]
    f0 = pd.Series(R.window_features(seg))
    f1 = pd.Series(R.window_features((seg - 3.7) / 5.3))
    rel = ((f1 - f0).abs() / (f0.abs() + 1e-12))
    changed = sorted(rel[rel > 1e-6].index.tolist())
    return dict(features_changed_by_affine_rescaling=changed, n_changed=len(changed), n_features=len(f0))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=["DEAP", "DREAMER"])
    ap.add_argument("--target", required=True, choices=C.TARGETS)
    ap.add_argument("--identity-check", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    D = C.load(a.dataset); X, r, subj, trial = D["X"], D["ratings"][a.target], D["subj"], D["trial"]
    calib = calibration_mask(subj, trial, N_CALIB[a.dataset])
    Dp = C.draws(subj)
    out_dir = C.OUT / "e4"; (out_dir / "oof").mkdir(parents=True, exist_ok=True)
    res = dict(dataset=a.dataset, target=a.target, protocol="P4 (leave-one-participant-out)",
               calibration_trials_per_participant=N_CALIB[a.dataset],
               scored_trials=int(len(np.unique(trial[~calib]))), leakage=LEAKAGE, arms={}, contrasts={})
    if a.identity_check and a.dataset == "DEAP":
        res["affine_invariance_check"] = check_affine_invariance()

    rows = []
    idx = np.arange(len(X))
    for f, (tr_all, te_all) in enumerate(C.splits("P4", subj, trial)):
        tr = tr_all[~calib[tr_all]]; te = te_all[~calib[te_all]]
        y, thr = C.labels(r, tr, "global", subj)
        for arm in ARMS:
            Z = normalize(arm, X, subj, tr, te, calib)
            for L in LEARNERS:
                rows.append(pd.DataFrame(dict(arm=arm, learner=L, fold=f, subj=subj[te], trial=trial[te],
                                              y=y[te], score=fit_predict(L, Z[tr], y[tr], Z[te]))))
        if f % 8 == 0:
            print(f"{a.dataset}/{a.target} fold {f}  [{time.time()-t0:.0f}s]", flush=True)
    W = pd.concat(rows, ignore_index=True)
    T = (W.groupby(["arm", "learner", "trial"], sort=True)
          .agg(subj=("subj", "first"), y=("y", "first"), fold=("fold", "first"), score=("score", "mean")).reset_index())
    T.to_parquet(out_dir / "oof" / f"{a.dataset}_{a.target}_trials.parquet")
    boots = {}
    for (arm, L), g in T.groupby(["arm", "learner"]):
        summ, b = C.summarize(g.y.to_numpy(), g.score.to_numpy(), g.subj.to_numpy(), Dp)
        summ["within_participant_auc"] = C.within_fold_auc(g.y.to_numpy(), g.score.to_numpy(), g.fold.to_numpy())
        res["arms"].setdefault(L, {})[arm] = summ; boots[(arm, L)] = b
        print(f"  {L} {arm}: {summ['auc']:.3f} {summ['ci']} within {summ['within_participant_auc']:.3f}", flush=True)
    for L in LEARNERS:
        pt = {arm: res["arms"][L][arm]["auc"] for arm in ARMS}
        cc = {f"{arm}-A": C.paired(pt[arm], pt["A"], boots[(arm, L)], boots[("A", L)]) for arm in ["none", "D", "B", "C"]}
        cc["C-B"] = C.paired(pt["C"], pt["B"], boots[("C", L)], boots[("B", L)])
        res["contrasts"][L] = cc

    if a.identity_check:
        s0 = np.searchsorted(np.unique(subj), subj)
        sc = ~calib
        res["identity_probe"] = {}
        for arm in ["none", "A", "B", "C"]:
            Z = normalize(arm, X, subj, idx[sc], idx[sc], calib) if arm != "A" else zscore(X, sc)
            out = {}
            for L in LEARNERS:
                accs = []
                for k, (itr, ite) in enumerate(GroupKFold(5).split(Z[sc], groups=trial[sc])):
                    if L == "xgb" and k > 0:
                        break
                    m = (XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.2, random_state=0, n_jobs=4, verbosity=0)
                         if L == "xgb" else LogisticRegression(max_iter=5000))
                    accs.append(accuracy_score(s0[sc][ite], m.fit(Z[sc][itr], s0[sc][itr]).predict(Z[sc][ite])))
                out[L] = dict(accuracy=float(np.mean(accs)), folds=len(accs))
            res["identity_probe"][arm] = out
            print(f"  identity after {arm}: {out}  [{time.time()-t0:.0f}s]", flush=True)
        res["identity_probe_note"] = ("scored rows of all participants; trial-grouped GroupKFold(5); logistic regression "
                                      "on all 5 folds, XGBoost on the first fold; A and D coincide here (one global z-score)")
    res["_manifest"] = C.manifest("rev1_e4_normalization.py", runtime_s=round(time.time() - t0, 1))
    C.dump(res, out_dir / f"{a.dataset}_{a.target}.json")
    print(f"done in {time.time()-t0:.0f}s", flush=True)
