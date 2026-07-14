"""
Corrected and extended protocol sweep for the Perspective demonstration.

Fixes and additions relative to the original notebook:

  1. ADDS the missing intermediate split (trial-grouped, participant-pooled): no trial is
     split across the train/test boundary, but the same participants appear on both sides.
     This is what separates correlated-window leakage from participant overlap:
        P1 -> P2  = correlated-window effect
        P2 -> P3  = participant-overlap (identity) effect
        P3 -> P4  = evaluation-unit effect
  2. FIXES the bootstrap. The original resampled ROWS (windows), which produces falsely narrow
     intervals and is exactly the error the paper's own checklist warns against. All intervals
     here resample SUBJECTS, the unit of independence.
  3. ADDS a second label scheme. The original used a GLOBAL median (which leaves per-subject
     base rates skewed, so the participant-specific label-prior channel is active). We report
     the global median as the population-level target and a PER-SUBJECT median as a sensitivity
     analysis that neutralizes the subject label prior, and we report per-subject base rates.
  4. Reports per-fold AUCs and per-fold positive rates, to diagnose the below-chance cell.
  5. Writes machine-readable JSON (the original only printed to stdout).

Features/loaders are identical to the original notebook (66 features, 6 frontal channels).
"""
from __future__ import annotations
import os, pickle, time, json, warnings
from pathlib import Path
import numpy as np, pandas as pd
import scipy.io as sio
from scipy.signal import welch
import antropy as ant
from sklearn.model_selection import StratifiedKFold, GroupKFold, LeaveOneGroupOut
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, accuracy_score
from xgboost import XGBClassifier
warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
# Point QEEG_DATA_ROOT at the folder holding data/deap/data_preprocessed_python/ and DREAMER.mat
ROOT = Path(os.environ.get("QEEG_DATA_ROOT", HERE / "../.."))
DEAP_DIR    = ROOT / "data/deap/data_preprocessed_python"
DREAMER_MAT = ROOT / "DREAMER.mat"
CACHE = HERE / "cache"; CACHE.mkdir(exist_ok=True)
OUT = HERE / "../results"; OUT.mkdir(exist_ok=True)

FS, BASELINE_S, WIN_S, STEP_S, DREAMER_LAST_S, SEED = 128, 3, 4, 2, 60, 17
CH = ["AF3", "F3", "F7", "AF4", "F4", "F8"]
DEAP_IDX = {"AF3":1, "F3":2, "F7":3, "AF4":17, "F4":19, "F8":20}
DREAMER_ORDER = ['AF3','F7','F3','FC5','T7','P7','O1','O2','P8','T8','FC6','F4','F8','AF4']
BANDS = {"delta":(1,4),"theta":(4,8),"alpha":(8,13),"beta":(13,30),"gamma":(30,45)}
np.random.seed(SEED)


# ---------------------------------------------------------------- features (unchanged)
def window_features(seg):
    d = {}
    for ci, name in enumerate(CH):
        x = seg[ci]
        f, p = welch(x, FS, nperseg=min(len(x), FS*2)); tot = np.trapz(p, f) + 1e-12
        bp = {b: np.trapz(p[(f>=lo)&(f<hi)], f[(f>=lo)&(f<hi)])/tot for b,(lo,hi) in BANDS.items()}
        for b in BANDS: d[f"{name}_{b}_rel"] = bp[b]
        d[f"{name}_theta_alpha"] = bp["theta"]/(bp["alpha"]+1e-9)
        d[f"{name}_theta_beta"]  = bp["theta"]/(bp["beta"]+1e-9)
        dx, ddx = np.diff(x), np.diff(np.diff(x)); v = np.var(x)+1e-12
        mob = np.sqrt((np.var(dx)+1e-12)/v)
        d[f"{name}_hjorth_act"]  = v
        d[f"{name}_hjorth_mob"]  = mob
        d[f"{name}_hjorth_comp"] = np.sqrt((np.var(ddx)+1e-12)/(np.var(dx)+1e-12))/(mob+1e-12)
        d[f"{name}_perm_entropy"] = ant.perm_entropy(x, order=3, normalize=True)
    return d


def _windows(sig):
    n = sig.shape[1]
    return [window_features(sig[:, st:st+WIN_S*FS]) for st in range(0, n-WIN_S*FS+1, STEP_S*FS)]


def load_deap():
    idx = [DEAP_IDX[c] for c in CH]; rows, val, aro, subj, trial = [], [], [], [], []
    for sf in sorted(DEAP_DIR.glob("s*.dat")):
        s = int(sf.stem[1:]); dd = pickle.load(open(sf,"rb"), encoding="latin1")
        for t in range(dd["data"].shape[0]):
            sig = dd["data"][t, idx, BASELINE_S*FS:]
            w = _windows(sig); rows += w
            val += [dd["labels"][t,0]]*len(w); aro += [dd["labels"][t,1]]*len(w)
            subj += [s]*len(w); trial += [f"{s}_{t}"]*len(w)
    return pd.DataFrame(rows).values, np.array(val), np.array(aro), np.array(subj), np.array(trial)


def load_dreamer():
    idx = [DREAMER_ORDER.index(c) for c in CH]; rows, val, aro, subj, trial = [], [], [], [], []
    D = sio.loadmat(DREAMER_MAT, struct_as_record=False, squeeze_me=True)["DREAMER"]
    for si, s in enumerate(D.Data):
        sv, sa = np.array(s.ScoreValence), np.array(s.ScoreArousal)
        for t in range(len(s.EEG.stimuli)):
            sig = np.array(s.EEG.stimuli[t]).T[idx, -DREAMER_LAST_S*FS:]
            w = _windows(sig); rows += w
            val += [sv[t]]*len(w); aro += [sa[t]]*len(w)
            subj += [si]*len(w); trial += [f"{si}_{t}"]*len(w)
    return pd.DataFrame(rows).values, np.array(val), np.array(aro), np.array(subj), np.array(trial)


def get_data(name):
    f = CACHE / f"{name}.npz"
    if f.exists():
        z = np.load(f, allow_pickle=True)
        return z["X"], z["val"], z["aro"], z["subj"], z["trial"]
    X, val, aro, subj, trial = (load_deap if name == "DEAP" else load_dreamer)()
    np.savez_compressed(f, X=X, val=val, aro=aro, subj=subj, trial=trial)
    return X, val, aro, subj, trial


# ---------------------------------------------------------------- labels
def labels_global_median(r):
    return (r >= np.median(r)).astype(int)


def labels_subject_median(r, subj):
    y = np.zeros(len(r), int)
    for s in np.unique(subj):
        m = subj == s
        y[m] = (r[m] >= np.median(r[m])).astype(int)
    return y


def base_rate_spread(y, subj):
    rates = [float(y[subj == s].mean()) for s in np.unique(subj)]
    return dict(mean=float(np.mean(rates)), sd=float(np.std(rates)),
                min=float(np.min(rates)), max=float(np.max(rates)))


# ---------------------------------------------------------------- model + subject bootstrap
def model():
    return XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.1,
                         subsample=0.8, colsample_bytree=0.8, eval_metric="logloss",
                         random_state=SEED, n_jobs=4, verbosity=0)


def boot_ci_subject(y, p, subj, n=1000, seed=SEED):
    """95% CI resampling SUBJECTS (the unit of independence), not rows."""
    rng = np.random.default_rng(seed)
    subs = np.unique(subj)
    by = {s: np.where(subj == s)[0] for s in subs}
    out = []
    for _ in range(n):
        bs = rng.choice(subs, len(subs), replace=True)
        idx = np.concatenate([by[s] for s in bs])
        if len(np.unique(y[idx])) == 2:
            out.append(roc_auc_score(y[idx], p[idx]))
    if not out:
        return (float("nan"), float("nan"))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def _fit_oof(X, y, splits, scale=False):
    oof = np.zeros(len(y)); folds = []
    for tr, te in splits:
        if scale:
            sc = StandardScaler().fit(X[tr])
            Xtr, Xte = sc.transform(X[tr]), sc.transform(X[te])
        else:
            Xtr, Xte = X[tr], X[te]
        m = model(); m.fit(Xtr, y[tr])
        oof[te] = m.predict_proba(Xte)[:, 1]
        fa = roc_auc_score(y[te], oof[te]) if len(np.unique(y[te])) == 2 else float("nan")
        folds.append(dict(auc=float(fa), pos_rate=float(y[te].mean()), n=int(len(te))))
    return oof, folds


# ---------------------------------------------------------------- the four protocols
def p1_window_pooled(X, y, subj, trial):
    sp = list(StratifiedKFold(5, shuffle=True, random_state=SEED).split(X, y))
    oof, folds = _fit_oof(X, y, sp)
    return roc_auc_score(y, oof), boot_ci_subject(y, oof, subj), folds


def p2_trial_grouped(X, y, subj, trial):
    """NEW: no shared trial across the split, but the same participants are on both sides."""
    sp = list(GroupKFold(5).split(X, y, groups=trial))
    oof, folds = _fit_oof(X, y, sp)
    return roc_auc_score(y, oof), boot_ci_subject(y, oof, subj), folds


def p3_subject_grouped(X, y, subj, trial):
    sp = list(GroupKFold(5).split(X, y, groups=subj))
    oof, folds = _fit_oof(X, y, sp)
    return roc_auc_score(y, oof), boot_ci_subject(y, oof, subj), folds


def p4_loso_trial(X, y, subj, trial):
    preds, trues, tsubj, folds = [], [], [], []
    for tr, te in LeaveOneGroupOut().split(X, y, groups=subj):
        sc = StandardScaler().fit(X[tr]); m = model(); m.fit(sc.transform(X[tr]), y[tr])
        p = m.predict_proba(sc.transform(X[te]))[:, 1]; tt = trial[te]
        fp, ft = [], []
        for ut in np.unique(tt):
            fp.append(p[tt == ut].mean()); ft.append(y[te][tt == ut][0])
        preds += fp; trues += ft; tsubj += [subj[te][0]] * len(fp)
        fa = roc_auc_score(ft, fp) if len(np.unique(ft)) == 2 else float("nan")
        folds.append(dict(auc=float(fa), pos_rate=float(np.mean(ft)), n=len(fp)))
    preds, trues, tsubj = np.array(preds), np.array(trues), np.array(tsubj)
    return roc_auc_score(trues, preds), boot_ci_subject(trues, preds, tsubj), folds


def subject_id_acc(X, subj, trial):
    s0 = subj - subj.min(); oof = np.zeros(len(s0), int)
    for tr, te in GroupKFold(5).split(X, s0, groups=trial):
        m = XGBClassifier(n_estimators=150, max_depth=4, learning_rate=0.2, n_jobs=4, verbosity=0)
        m.fit(X[tr], s0[tr]); oof[te] = m.predict(X[te])
    return float(accuracy_score(s0, oof)), 1.0 / len(set(s0.tolist()))


PROTOCOLS = [("P1_window_pooled", p1_window_pooled),
             ("P2_trial_grouped_participant_pooled", p2_trial_grouped),
             ("P3_subject_grouped_windows", p3_subject_grouped),
             ("P4_loso_trial", p4_loso_trial)]

SCHEMES = [("global_median", labels_global_median),
           ("subject_median", labels_subject_median)]

if __name__ == "__main__":
    t0 = time.time(); RES = {}
    for name in ["DEAP", "DREAMER"]:
        X, val, aro, subj, trial = get_data(name)
        print(f"\n{'='*78}\n{name}: {X.shape[0]} windows x {X.shape[1]} feats, "
              f"{len(set(subj.tolist()))} subjects   [{time.time()-t0:.0f}s]\n{'='*78}", flush=True)
        sid, chance = subject_id_acc(X, subj, trial)
        RES[name] = dict(n_windows=int(X.shape[0]), n_subjects=int(len(set(subj.tolist()))),
                         subject_id_acc=sid, subject_id_chance=chance, schemes={})
        print(f"subject-identity decoding: {sid:.3f} (chance {chance:.3f})", flush=True)

        for sch_name, sch_fn in SCHEMES:
            RES[name]["schemes"][sch_name] = {}
            for tgt, r in [("valence", val), ("arousal", aro)]:
                y = sch_fn(r) if sch_name == "global_median" else sch_fn(r, subj)
                br = base_rate_spread(y, subj)
                print(f"\n--- {name} / {sch_name} / {tgt} : overall pos-rate {y.mean():.3f}, "
                      f"per-subject base rate {br['mean']:.2f} +/- {br['sd']:.2f} "
                      f"(min {br['min']:.2f}, max {br['max']:.2f})", flush=True)
                cell = dict(pos_rate=float(y.mean()), base_rate=br, protocols={})
                for pname, fn in PROTOCOLS:
                    auc, ci, folds = fn(X, y, subj, trial)
                    cell["protocols"][pname] = dict(auc=float(auc), ci=list(ci), folds=folds)
                    print(f"  {pname:38s} AUC {auc:.3f}  95% CI (subject-boot) "
                          f"[{ci[0]:.3f}, {ci[1]:.3f}]   [{time.time()-t0:.0f}s]", flush=True)
                RES[name]["schemes"][sch_name][tgt] = cell

    (OUT / "protocols.json").write_text(json.dumps(RES, indent=2))
    print(f"\nDONE in {time.time()-t0:.0f}s -> {OUT/'protocols.json'}")
