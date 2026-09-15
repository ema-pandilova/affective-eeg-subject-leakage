"""
E3 (Frontiers revision): does removing identity-discriminative directions remove the participant-overlap advantage?

Transformation, fitted on the TRAINING rows of each fold only and then applied unchanged to the test rows:
    1. standardize each feature with the training mean and SD;
    2. whiten with the training within-participant covariance (symmetric inverse square root, small ridge);
    3. compute the training participants' mean vectors in the whitened space and take their principal
       directions (in whitened space these are the linear discriminant directions for identity);
    4. project out the top k directions.  k = 0 is the whitened representation with nothing removed.
Control: project out k random orthonormal directions instead (two draws per k), to separate removing
identity from simply discarding k dimensions.

Evaluation: P2 (participants on both sides) and P3 (participants disjoint), same folds and training-only
label threshold as E1, XGBoost (the paper's model) and logistic regression (for which linear removal is complete).
The identity account predicts that removal lowers P2 toward P3 while leaving P3 largely unchanged, and that
random removal does not. Any other pattern is reported as found.

Manipulation check (first fold of each protocol):
    P2  identity classifier trained on transformed training rows, scored on the transformed test rows
        (same participants, unseen trials)
    P3  identity decodability among the held-out participants only, with a transform fitted without them
        (trial-grouped 5-fold within the test participants)

    python rev1_e3_identity_removal.py --dataset DEAP --target valence [--identity-check]
"""
from __future__ import annotations
import argparse, time
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.metrics import accuracy_score, roc_auc_score
from xgboost import XGBClassifier
import rev1_common as C

K_GRID = {"DEAP": [0, 4, 8, 16, 24], "DREAMER": [0, 4, 8, 16]}
N_RANDOM = 2
LEARNERS = ["xgb", "logreg"]


class IdentityRemoval:
    def __init__(self, X, subj):
        self.mu = X.mean(0); self.sd = X.std(0) + 1e-12
        Z = (X - self.mu) / self.sd
        means = pd.DataFrame(Z).groupby(subj).transform("mean").to_numpy()
        Rw = Z - means
        S = Rw.T @ Rw / (len(Rw) - 1)
        S += np.eye(len(S)) * 1e-3 * np.trace(S) / len(S)
        ev, Q = np.linalg.eigh(S)
        self.W = Q @ np.diag(ev ** -0.5) @ Q.T
        A = Z @ self.W
        M = pd.DataFrame(A).groupby(subj).mean().to_numpy()
        M = M - M.mean(0)
        _, sv, Vt = np.linalg.svd(M, full_matrices=False)
        self.Vt, self.sv2 = Vt, sv ** 2
        self.rank = int((sv > 1e-10 * sv.max()).sum())

    def whiten(self, X):
        return ((X - self.mu) / self.sd) @ self.W

    def remove(self, A, k, random_seed=None):
        if k == 0:
            return A
        if random_seed is None:
            V = self.Vt[:k]
        else:
            G = np.random.default_rng(random_seed).standard_normal((A.shape[1], k))
            V = np.linalg.qr(G)[0].T
        return A - (A @ V.T) @ V

    def between_share(self, k):
        return float(self.sv2[:k].sum() / self.sv2.sum())


def fit_predict(learner, Xtr, ytr, Xte):
    if learner == "xgb":
        return C.xgb().fit(Xtr, ytr).predict_proba(Xte)[:, 1]
    return LogisticRegression(max_iter=3000).fit(Xtr, ytr).predict_proba(Xte)[:, 1]


def id_acc(learner, Xtr, str_, Xte, ste):
    if learner == "xgb":
        m = XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.2, random_state=0, n_jobs=4, verbosity=0)
    else:
        m = LogisticRegression(max_iter=3000)
    lab = np.unique(str_)
    return float(accuracy_score(np.searchsorted(lab, ste), m.fit(Xtr, np.searchsorted(lab, str_)).predict(Xte)))


def conditions(ks):
    out = [("identity", k, None) for k in ks]
    out += [("random", k, d) for k in ks if k > 0 for d in range(N_RANDOM)]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=["DEAP", "DREAMER"])
    ap.add_argument("--target", required=True, choices=C.TARGETS)
    ap.add_argument("--identity-check", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    D = C.load(a.dataset); X, r, subj, trial, stim = D["X"], D["ratings"][a.target], D["subj"], D["trial"], D["stim"]
    Dp = C.draws(subj); ks = K_GRID[a.dataset]; conds = conditions(ks)
    out_dir = C.OUT / "e3"; (out_dir / "oof").mkdir(parents=True, exist_ok=True)
    res = dict(dataset=a.dataset, target=a.target, k_grid=ks, n_random=N_RANDOM, protocols={}, identity_check={})

    for p in ["P2", "P3"]:
        rows = []; fold_info = []
        for f, (tr, te) in enumerate(C.splits(p, subj, trial, C.SEED)):
            y, thr = C.labels(r, tr, "global", subj)
            T = IdentityRemoval(X[tr], subj[tr])
            assert T.rank >= max(ks), (T.rank, ks)
            Atr, Ate = T.whiten(X[tr]), T.whiten(X[te])
            fold_info.append(dict(rank=T.rank, between_share={k: T.between_share(k) for k in ks}, threshold=thr))
            for kind, k, d in conds:
                seed = None if kind == "identity" else 10_000 * (f + 1) + 100 * k + d
                Btr, Bte = T.remove(Atr, k, seed), T.remove(Ate, k, seed)
                for L in LEARNERS:
                    pr = fit_predict(L, Btr, y[tr], Bte)
                    rows.append(pd.DataFrame(dict(protocol=p, fold=f, kind=kind, k=k, draw=-1 if d is None else d,
                                                  learner=L, row=te, subj=subj[te], trial=trial[te], stim=stim[te],
                                                  y=y[te], score=pr)))
                if a.identity_check and f == 0:
                    for L in LEARNERS:
                        if p == "P2":
                            acc = id_acc(L, Btr, subj[tr], Bte, subj[te]); chance = 1 / len(np.unique(subj[tr]))
                        else:
                            accs = []
                            for itr, ite in GroupKFold(5).split(Bte, groups=trial[te]):
                                accs.append(id_acc(L, Bte[itr], subj[te][itr], Bte[ite], subj[te][ite]))
                            acc = float(np.mean(accs)); chance = 1 / len(np.unique(subj[te]))
                        res["identity_check"].setdefault(p, []).append(
                            dict(kind=kind, k=k, draw=d, learner=L, accuracy=acc, chance=chance))
            print(f"{a.dataset}/{a.target}/{p} fold {f} done (rank {T.rank})  [{time.time()-t0:.0f}s]", flush=True)
        W = pd.concat(rows, ignore_index=True)
        # trial level: mean window score within (condition, trial)
        keys = ["kind", "k", "draw", "learner"]
        Tt = (W.groupby(keys + ["trial"], sort=True)
                .agg(subj=("subj", "first"), stim=("stim", "first"), y=("y", "first"), fold=("fold", "first"),
                     score=("score", "mean")).reset_index())
        Tt.to_parquet(out_dir / "oof" / f"{a.dataset}_{a.target}_{p}_trials.parquet")
        entry = dict(folds=fold_info, conditions=[])
        boots = {}
        for key, g in Tt.groupby(keys, sort=True):
            summ, b = C.summarize(g.y.to_numpy(), g.score.to_numpy(), g.subj.to_numpy(), Dp)
            boots[key] = b
            entry["conditions"].append(dict(zip(keys, key), **summ))
        res["protocols"][p] = entry
        res.setdefault("_boots", {})[p] = boots
        for c in entry["conditions"]:
            if c["kind"] == "identity" and c["learner"] == "xgb":
                print(f"  {p} xgb k={c['k']}: {c['auc']:.3f} {c['ci']}", flush=True)

    # contrasts: change from k=0 within protocol, the P2-vs-P3 difference in change, and identity vs random removal
    boots = res.pop("_boots")
    pt = {(p, c["kind"], c["k"], c["draw"], c["learner"]): c["auc"] for p in ["P2", "P3"] for c in res["protocols"][p]["conditions"]}
    con = []
    for L in LEARNERS:
        for k in ks[1:]:
            e = {}
            for p in ["P2", "P3"]:
                base, bb = pt[(p, "identity", 0, -1, L)], boots[p][("identity", 0, -1, L)]
                idk, ib = pt[(p, "identity", k, -1, L)], boots[p][("identity", k, -1, L)]
                rnd = np.mean([pt[(p, "random", k, d, L)] for d in range(N_RANDOM)])
                rb = np.mean([boots[p][("random", k, d, L)] for d in range(N_RANDOM)], axis=0)
                e[f"{p}: identity k - k0"] = C.paired(idk, base, ib, bb)
                e[f"{p}: random k - k0"] = C.paired(rnd, base, rb, bb)
                e[f"{p}: identity k - random k"] = C.paired(idk, rnd, ib, rb)
                e[f"_{p}"] = (idk - base, ib - bb)
            (d2, b2), (d3, b3) = e.pop("_P2"), e.pop("_P3")
            e["(P2 change) - (P3 change)"] = dict(diff=float(d2 - d3), ci=C.ci(b2 - b3))
            con.append(dict(learner=L, k=k, **e))
    res["contrasts"] = con
    res["_manifest"] = C.manifest("rev1_e3_identity_removal.py", runtime_s=round(time.time() - t0, 1))
    C.dump(res, out_dir / f"{a.dataset}_{a.target}.json")
    print(f"done in {time.time()-t0:.0f}s", flush=True)
