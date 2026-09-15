"""
E5 (Frontiers revision): unseen participants with previously seen stimuli versus unseen participants with unseen
stimuli, in a size-matched participant-block x stimulus-block design.

Participants are dealt at random (fixed seed, before and independent of any label) into Ks blocks and stimuli
into Kv blocks (DEAP 8 x 5, DREAMER 6 x 6); every participant saw every stimulus, so the trials form a full grid.
Each cell (participant block i, stimulus block j) is a test set once. For that test cell the two arms train on

    seen stimulus    (US): participant blocks != i, stimulus blocks != j+1 (mod Kv)
    unseen stimulus  (UU): participant blocks != i, stimulus blocks != j

so both arms use the same training participants, the same number of trials and the same number of stimuli, and
differ only in whether the test stimuli were seen (through other participants) during training. Asserted per
fold: no participant or trial overlap in either arm, no stimulus overlap in UU, all test stimuli seen in US,
equal training size.

LOSO with shared stimuli (P4) measures generalization to unseen participants under previously observed stimuli;
the UU arm measures the harder unseen-participant and unseen-stimulus condition.

Scores: EEG (XGBoost, training-only label threshold), the training positive rate, and the no-EEG stimulus prior
(informative only in US). Trial-level pooled AUC with 95% participant-bootstrap intervals and, because stimuli
are also sampled, crossed participant x stimulus bootstrap intervals; US - UU differences are paired.

    python rev1_e5_stimulus.py --dataset DEAP --seeds 17
"""
from __future__ import annotations
import argparse, time
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
import rev1_common as C

BLOCKS = {"DEAP": (8, 5), "DREAMER": (6, 6), "FACED": (8, 7)}
ARMS = ["US", "UU"]
SCORES = ["eeg", "prior_global", "prior_stimulus"]


def assign_blocks(ids, K, rng):
    perm = rng.permutation(np.unique(ids))
    return {u: n % K for n, u in enumerate(perm)}


def factorial_folds(subj, stim, Ks, Kv, seed):
    rng = np.random.default_rng(seed)
    sb = assign_blocks(subj, Ks, rng); vb = assign_blocks(stim, Kv, rng)
    rb = np.array([sb[u] for u in subj]); cb = np.array([vb[u] for u in stim])
    folds = []
    for i in range(Ks):
        for j in range(Kv):
            te = np.where((rb == i) & (cb == j))[0]
            arms = {"US": np.where((rb != i) & (cb != (j + 1) % Kv))[0],
                    "UU": np.where((rb != i) & (cb != j))[0]}
            folds.append((i, j, te, arms))
    return folds, sb, vb


def check_fold(te, arms, subj, trial, stim):
    for arm, tr in arms.items():
        assert not set(subj[tr]) & set(subj[te]), "participant overlap"
        assert not set(trial[tr]) & set(trial[te]), "trial overlap"
    assert not set(stim[arms["UU"]]) & set(stim[te]), "stimulus overlap in UU"
    assert set(stim[te]) <= set(stim[arms["US"]]), "US must have seen the test stimuli"
    assert len(arms["US"]) == len(arms["UU"]), "training sizes differ"
    assert set(subj[arms["US"]]) == set(subj[arms["UU"]]), "training participants differ"


def run(D, target, seed):
    X, r, subj, trial, stim = D["X"], D["ratings"][target], D["subj"], D["trial"], D["stim"]
    Ks, Kv = BLOCKS[D["name"]]
    folds, sb, vb = factorial_folds(subj, stim, Ks, Kv, seed)
    rows, info = [], []
    for f, (i, j, te, arms) in enumerate(folds):
        check_fold(te, arms, subj, trial, stim)
        for arm, tr in arms.items():
            y, thr = C.labels(r, tr, "global", subj)
            g = float(y[tr].mean())
            rows.append(pd.DataFrame(dict(arm=arm, fold=f, subj=subj[te], trial=trial[te], stim=stim[te], y=y[te],
                                          eeg=C.xgb().fit(X[tr], y[tr]).predict_proba(X[te])[:, 1],
                                          prior_global=g, prior_stimulus=C.rate_by(y[tr], stim[tr], stim[te], g))))
            info.append(dict(fold=f, arm=arm, n_train=int(len(tr)), n_test=int(len(te)), threshold=thr,
                             train_participants=int(len(np.unique(subj[tr]))), train_stimuli=int(len(np.unique(stim[tr]))),
                             test_participants=int(len(np.unique(subj[te]))), test_stimuli=int(len(np.unique(stim[te])))))
    W = pd.concat(rows, ignore_index=True)
    T = (W.groupby(["arm", "trial"], sort=True)
          .agg(subj=("subj", "first"), stim=("stim", "first"), y=("y", "first"), fold=("fold", "first"),
               **{s: (s, "mean") for s in SCORES}).reset_index())
    for arm in ARMS:
        assert T[T.arm == arm].trial.nunique() == len(np.unique(trial)), "every trial is tested once per arm"
    return T, info, dict(participant_blocks={str(k): int(v) for k, v in sb.items()},
                         stimulus_blocks={str(k): int(v) for k, v in vb.items()})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=["DEAP", "DREAMER", "FACED"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[C.SEED])
    a = ap.parse_args()
    t0 = time.time()
    D = C.load(a.dataset)
    Dp = C.draws(D["subj"]); Sv = C.stim_draws(D["stim"])
    out_dir = C.OUT / "e5"; (out_dir / "oof").mkdir(parents=True, exist_ok=True)
    for seed in a.seeds:
        res = dict(dataset=a.dataset, seed=seed, blocks=BLOCKS[a.dataset], targets={})
        for target in C.TARGETS:
            T, info, blocks = run(D, target, seed)
            T.to_parquet(out_dir / "oof" / f"{a.dataset}_{target}_seed{seed}_trials.parquet")
            cell = dict(folds=info, blocks=blocks, arms={}, contrasts={})
            bp, bx = {}, {}
            for arm in ARMS:
                g = T[T.arm == arm].sort_values("trial")
                cell["arms"][arm] = {}
                for s in SCORES:
                    summ, b = C.summarize(g.y.to_numpy(), g[s].to_numpy(), g.subj.to_numpy(), Dp)
                    bxs = C.boot_aucs(g.y.to_numpy(), g[s].to_numpy(), g.subj.to_numpy(), Dp, g.stim.to_numpy(), Sv)
                    summ["ci_crossed"] = C.ci(bxs)
                    cell["arms"][arm][s] = summ; bp[(arm, s)] = b; bx[(arm, s)] = bxs
            for s in ["eeg", "prior_stimulus"]:
                us, uu = cell["arms"]["US"][s]["auc"], cell["arms"]["UU"][s]["auc"]
                cell["contrasts"][f"{s}: US-UU"] = dict(
                    diff=float(us - uu), ci=C.ci(bp[("US", s)] - bp[("UU", s)]),
                    ci_crossed=C.ci(bx[("US", s)] - bx[("UU", s)]))
            res["targets"][target] = cell
            e = cell["arms"]
            print(f"{a.dataset}/{target}/seed {seed}: EEG US {e['US']['eeg']['auc']:.3f} {e['US']['eeg']['ci']} | "
                  f"UU {e['UU']['eeg']['auc']:.3f} {e['UU']['eeg']['ci']} | stim-prior US {e['US']['prior_stimulus']['auc']:.3f} "
                  f"UU {e['UU']['prior_stimulus']['auc']:.3f}  [{time.time()-t0:.0f}s]", flush=True)
        res["_manifest"] = C.manifest("rev1_e5_stimulus.py", runtime_s=round(time.time() - t0, 1))
        C.dump(res, out_dir / f"{a.dataset}_seed{seed}.json")
    print(f"done in {time.time()-t0:.0f}s", flush=True)
