"""
E1 + E2 (Frontiers revision): exact P1-P4 results on corrected DEAP labels with training-only label thresholds,
and baselines that use no EEG, computed on the identical folds and labels.

Scores per test window
    eeg                 XGBoost on the 66 features
    prior_global        training-fold positive rate (one constant per fold)
    prior_participant   the test participant's positive rate in the training rows; the global training rate
                        when that participant is absent from training (P3, P4)
    prior_stimulus      the test stimulus's positive rate in the training rows (stimulus-label shortcut)
No held-out label enters any prior: every rate is computed from y[train] after the fold is fixed.

Also: partition variability (P1-P3 refit on four further fold seeds) and the subject-identity probe.

    python rev1_e1_protocols.py --dataset DEAP --scheme global
Writes results/rev1/e1/<dataset>_<scheme>.json and oof/<dataset>_<scheme>_<target>_<protocol>.parquet
"""
from __future__ import annotations
import argparse, time
import numpy as np, pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.metrics import accuracy_score, balanced_accuracy_score, roc_auc_score
from xgboost import XGBClassifier
import rev1_common as C

PROTOCOLS = ["P1", "P2", "P3", "P4"]
SCORES = ["eeg", "prior_global", "prior_participant", "prior_stimulus"]
EXTRA_SEEDS = [C.SEED + 1, C.SEED + 2, C.SEED + 3, C.SEED + 4]


def run_protocol(D, target, scheme, protocol, seed, priors=True):
    X, r, subj, trial, stim = D["X"], D["ratings"][target], D["subj"], D["trial"], D["stim"]
    n = len(r)
    sc = {k: np.full(n, np.nan) for k in (SCORES if priors else ["eeg"])}
    y_oof = np.full(n, -1); fold = np.full(n, -1); folds = []
    for k, (tr, te) in enumerate(C.splits(protocol, subj, trial, seed, D.get("block"))):
        y, thr = C.labels(r, tr, scheme, subj)
        sc["eeg"][te] = C.xgb().fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
        g = float(y[tr].mean())
        if priors:
            sc["prior_global"][te] = g
            sc["prior_participant"][te] = C.rate_by(y[tr], subj[tr], subj[te], g)
            sc["prior_stimulus"][te] = C.rate_by(y[tr], stim[tr], stim[te], g)
        y_oof[te] = y[te]; fold[te] = k
        folds.append(dict(n_train=int(len(tr)), n_test=int(len(te)), threshold=thr, train_pos=g,
                          test_pos=float(y[te].mean()), test_participants=int(len(np.unique(subj[te]))),
                          train_participants=int(len(np.unique(subj[tr])))))
    assert (fold >= 0).all() and (y_oof >= 0).all()
    df = pd.DataFrame(dict(subj=subj, trial=trial, stim=stim, y=y_oof, fold=fold, **sc))
    return df, folds


def identity_probe(D):
    """The submission's probe, unchanged: trial-grouped 5-fold, XGBoost 150 trees, depth 4, learning rate 0.2."""
    X, subj, trial = D["X"], D["subj"], D["trial"]
    s0 = np.searchsorted(np.unique(subj), subj); oof = np.zeros(len(s0), int)
    for tr, te in GroupKFold(5).split(X, s0, groups=trial):
        m = XGBClassifier(n_estimators=150, max_depth=4, learning_rate=0.2, random_state=0, n_jobs=8 if D["name"] == "FACED" else 4, verbosity=0)
        oof[te] = m.fit(X[tr], s0[tr]).predict(X[te])
    return dict(accuracy=float(accuracy_score(s0, oof)), balanced_accuracy=float(balanced_accuracy_score(s0, oof)),
                chance=1.0 / len(np.unique(s0)), unit="window", folds="GroupKFold(5) on trials, unshuffled")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=["DEAP", "DREAMER", "FACED"])
    ap.add_argument("--scheme", required=True, choices=["global", "participant"])
    a = ap.parse_args()
    t0 = time.time()
    D = C.load(a.dataset)
    Dp = C.draws(D["subj"])
    out_dir = C.OUT / "e1"; (out_dir / "oof").mkdir(parents=True, exist_ok=True)
    res = dict(dataset=a.dataset, scheme=a.scheme,
               counts=dict(windows=int(len(D["subj"])), trials=int(len(np.unique(D["trial"]))),
                           participants=int(len(np.unique(D["subj"]))), stimuli=int(len(np.unique(D["stim"]))),
                           windows_per_trial=sorted(set(pd.Series(D["trial"]).value_counts().tolist()))),
               targets={})
    if a.scheme == "global":
        res["identity_probe"] = C_probe = identity_probe(D)
        print(f"{a.dataset} identity probe {C_probe}  [{time.time()-t0:.0f}s]", flush=True)

    protocols = PROTOCOLS + (["P2B"] if a.dataset == "FACED" else [])
    for target in C.TARGETS:
        cell = dict(protocols={}, contrasts={}, partition_seeds={})
        trial_tables, boots = {}, {}
        for p in protocols:
            df, folds = run_protocol(D, target, a.scheme, p, C.SEED)
            df.to_parquet(out_dir / "oof" / f"{a.dataset}_{a.scheme}_{target}_{p}.parquet")
            T = C.to_trials(df, SCORES)
            trial_tables[p] = T
            entry = dict(folds=folds, trials_with_mixed_labels=int(T.label_mixed.sum()),
                         trial_positive_rate=float(T.y.mean()),
                         participant_positive_rate=dict(
                             min=float(T.groupby("subj").y.mean().min()), max=float(T.groupby("subj").y.mean().max())),
                         trial_level={}, window_level={})
            for s in SCORES:
                summ, b = C.summarize(T.y.to_numpy(), T[s].to_numpy(), T.subj.to_numpy(), Dp)
                summ["within_fold_auc"] = C.within_fold_auc(T.y.to_numpy(), T[s].to_numpy(), T.fold.to_numpy()) \
                    if p != "P1" else None
                entry["trial_level"][s] = summ; boots[(p, s)] = b
            for s in ["eeg", "prior_participant"]:
                summ, _ = C.summarize(df.y.to_numpy(), df[s].to_numpy(), df.subj.to_numpy(), Dp)
                entry["window_level"][s] = summ
            cell["protocols"][p] = entry
            tl = entry["trial_level"]
            print(f"{a.dataset}/{a.scheme}/{target}/{p}: EEG {tl['eeg']['auc']:.3f} {C.ci(boots[(p,'eeg')])} | "
                  f"prior-part {tl['prior_participant']['auc']:.3f} | prior-glob {tl['prior_global']['auc']:.3f} | "
                  f"prior-stim {tl['prior_stimulus']['auc']:.3f}  [{time.time()-t0:.0f}s]", flush=True)

        for p in protocols[1:]:
            assert (trial_tables[p].trial.to_numpy() == trial_tables["P1"].trial.to_numpy()).all()
        pt = {p: cell["protocols"][p]["trial_level"]["eeg"]["auc"] for p in PROTOCOLS}
        be = {p: boots[(p, "eeg")] for p in PROTOCOLS}
        cell["contrasts"] = {
            "P1-P2": C.paired(pt["P1"], pt["P2"], be["P1"], be["P2"]),
            "P2-P3": C.paired(pt["P2"], pt["P3"], be["P2"], be["P3"]),
            "P3-P4": C.paired(pt["P3"], pt["P4"], be["P3"], be["P4"]),
            "(P2-P3)-(P1-P2)": C.paired(pt["P2"] - pt["P3"], pt["P1"] - pt["P2"], be["P2"] - be["P3"], be["P1"] - be["P2"]),
        }
        if "P2B" in protocols:
            pt["P2B"] = cell["protocols"]["P2B"]["trial_level"]["eeg"]["auc"]; be["P2B"] = boots[("P2B", "eeg")]
            cell["contrasts"]["P2-P2B"] = C.paired(pt["P2"], pt["P2B"], be["P2"], be["P2B"])
            cell["contrasts"]["P2B-P3"] = C.paired(pt["P2B"], pt["P3"], be["P2B"], be["P3"])
        for p in protocols:
            tl = cell["protocols"][p]["trial_level"]
            for s in ["prior_participant", "prior_stimulus"]:
                cell["contrasts"][f"{p}: eeg-{s}"] = C.paired(tl["eeg"]["auc"], tl[s]["auc"], boots[(p, "eeg")], boots[(p, s)])

        for seed in EXTRA_SEEDS:
            cell["partition_seeds"][seed] = {}
            for p in ["P1", "P2", "P3"] + (["P2B"] if a.dataset == "FACED" else []):
                df, _ = run_protocol(D, target, a.scheme, p, seed, priors=False)
                T = C.to_trials(df, ["eeg"])
                cell["partition_seeds"][seed][p] = float(roc_auc_score(T.y, T.eeg))
            print(f"  partition seed {seed}: {cell['partition_seeds'][seed]}  [{time.time()-t0:.0f}s]", flush=True)
        res["targets"][target] = cell

    res["_manifest"] = C.manifest("rev1_e1_protocols.py", runtime_s=round(time.time() - t0, 1))
    C.dump(res, out_dir / f"{a.dataset}_{a.scheme}.json")
    print(f"done {a.dataset}/{a.scheme} in {time.time()-t0:.0f}s", flush=True)
