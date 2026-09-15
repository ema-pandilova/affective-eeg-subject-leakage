"""
Frontiers revision (rev1): the submitted four-protocol sweep, rerun with a selectable DEAP label source.

Features, model, label schemes, fold construction and the subject bootstrap are exactly those of
run_protocols.py, which is imported and never modified. The protocol functions are restated here only so
that out-of-fold predictions and fold assignments can be saved; --gate proves the restatement is faithful.

    --deap-labels dat         labels as read from the .dat mirror (what the submission used)
    --deap-labels corrected   official DEAP ratings, joined and checked by deap_labels.py

    --gate    compare every numeric value against the submitted results/protocols.json and exit 1 on any
              difference above 5e-4 (i.e. the submission is not reproduced to three decimals)

Everything is written under results/rev1/<tag>/; results/protocols.json is never touched.

    python rev1_protocols.py --deap-labels dat --tag gate_dat --gate
    python rev1_protocols.py --deap-labels corrected --tag corrected
"""
from __future__ import annotations
import argparse, json, platform, sys, time
from pathlib import Path
import numpy as np
import sklearn, xgboost, scipy
from sklearn.model_selection import StratifiedKFold, GroupKFold, LeaveOneGroupOut
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

import run_protocols as R
import deap_labels
from rev1_provenance import git_state

SUBMITTED = R.HERE / "../results/protocols.json"
TOL = 5e-4


def _fit_oof(X, y, splits, scale=False):
    oof = np.zeros(len(y)); fold_id = np.full(len(y), -1); folds = []
    for k, (tr, te) in enumerate(splits):
        if scale:
            sc = StandardScaler().fit(X[tr])
            Xtr, Xte = sc.transform(X[tr]), sc.transform(X[te])
        else:
            Xtr, Xte = X[tr], X[te]
        m = R.model(); m.fit(Xtr, y[tr])
        oof[te] = m.predict_proba(Xte)[:, 1]; fold_id[te] = k
        fa = roc_auc_score(y[te], oof[te]) if len(np.unique(y[te])) == 2 else float("nan")
        folds.append(dict(auc=float(fa), pos_rate=float(y[te].mean()), n=int(len(te))))
    assert (fold_id >= 0).all()
    return oof, fold_id, folds


def p1_window_pooled(X, y, subj, trial):
    sp = list(StratifiedKFold(5, shuffle=True, random_state=R.SEED).split(X, y))
    oof, fid, folds = _fit_oof(X, y, sp)
    return dict(auc=roc_auc_score(y, oof), ci=R.boot_ci_subject(y, oof, subj), folds=folds,
                unit="window", pred=oof, y=y, subj=subj, trial=trial, fold=fid)


def p2_trial_grouped(X, y, subj, trial):
    sp = list(GroupKFold(5).split(X, y, groups=trial))
    oof, fid, folds = _fit_oof(X, y, sp)
    return dict(auc=roc_auc_score(y, oof), ci=R.boot_ci_subject(y, oof, subj), folds=folds,
                unit="window", pred=oof, y=y, subj=subj, trial=trial, fold=fid)


def p3_subject_grouped(X, y, subj, trial):
    sp = list(GroupKFold(5).split(X, y, groups=subj))
    oof, fid, folds = _fit_oof(X, y, sp)
    return dict(auc=roc_auc_score(y, oof), ci=R.boot_ci_subject(y, oof, subj), folds=folds,
                unit="window", pred=oof, y=y, subj=subj, trial=trial, fold=fid)


def p4_loso_trial(X, y, subj, trial):
    preds, trues, tsubj, ttrial, tfold, folds = [], [], [], [], [], []
    for k, (tr, te) in enumerate(LeaveOneGroupOut().split(X, y, groups=subj)):
        sc = StandardScaler().fit(X[tr]); m = R.model(); m.fit(sc.transform(X[tr]), y[tr])
        p = m.predict_proba(sc.transform(X[te]))[:, 1]; tt = trial[te]
        fp, ft = [], []
        for ut in np.unique(tt):
            fp.append(p[tt == ut].mean()); ft.append(y[te][tt == ut][0])
        preds += fp; trues += ft; tsubj += [subj[te][0]] * len(fp)
        ttrial += list(np.unique(tt)); tfold += [k] * len(fp)
        fa = roc_auc_score(ft, fp) if len(np.unique(ft)) == 2 else float("nan")
        folds.append(dict(auc=float(fa), pos_rate=float(np.mean(ft)), n=len(fp)))
    preds, trues, tsubj = np.array(preds), np.array(trues), np.array(tsubj)
    return dict(auc=roc_auc_score(trues, preds), ci=R.boot_ci_subject(trues, preds, tsubj), folds=folds,
                unit="trial", pred=preds, y=trues, subj=tsubj, trial=np.array(ttrial), fold=np.array(tfold))


PROTOCOLS = [("P1_window_pooled", p1_window_pooled),
             ("P2_trial_grouped_participant_pooled", p2_trial_grouped),
             ("P3_subject_grouped_windows", p3_subject_grouped),
             ("P4_loso_trial", p4_loso_trial)]


def load(name, deap_source):
    X, val, aro, subj, trial = R.get_data(name)
    if name == "DEAP" and deap_source == "corrected":
        val, aro = deap_labels.corrected_for_windows(trial, val, aro)
    return X, val, aro, subj, trial


def compare(sub, new, path="", diffs=None):
    """Every numeric leaf of the submitted JSON must exist in the new one and agree within TOL."""
    diffs = [] if diffs is None else diffs
    if isinstance(sub, dict):
        for k, v in sub.items():
            if k not in new:
                diffs.append((f"{path}/{k}", "missing", None)); continue
            compare(v, new[k], f"{path}/{k}", diffs)
    elif isinstance(sub, list):
        if not isinstance(new, list) or len(new) != len(sub):
            diffs.append((path, "length", None))
        else:
            for i, (a, b) in enumerate(zip(sub, new)):
                compare(a, b, f"{path}[{i}]", diffs)
    elif isinstance(sub, (int, float)) and not isinstance(sub, bool):
        if not isinstance(new, (int, float)) or isinstance(new, bool):
            diffs.append((path, sub, repr(new)))
        elif np.isnan(sub) or np.isnan(new):
            if not (np.isnan(sub) and np.isnan(new)):
                diffs.append((path, sub, new))
        elif abs(sub - new) > TOL:
            diffs.append((path, sub, new))
    return diffs


def count_numeric(x):
    if isinstance(x, dict):
        return sum(count_numeric(v) for v in x.values())
    if isinstance(x, list):
        return sum(count_numeric(v) for v in x)
    return int(isinstance(x, (int, float)) and not isinstance(x, bool))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--deap-labels", choices=["dat", "corrected"], required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--datasets", nargs="+", default=["DEAP", "DREAMER"])
    ap.add_argument("--gate", action="store_true")
    a = ap.parse_args()
    assert not a.gate or sorted(a.datasets) == ["DEAP", "DREAMER"], "the gate must cover every submitted dataset"

    out = (R.HERE / "../results/rev1" / a.tag).resolve()
    assert out != SUBMITTED.parent.resolve()
    (out / "oof").mkdir(parents=True, exist_ok=True)

    t0 = time.time(); RES = {}
    for name in a.datasets:
        X, val, aro, subj, trial = load(name, a.deap_labels)
        print(f"\n{name}: {X.shape[0]} windows x {X.shape[1]} feats, {len(set(subj.tolist()))} subjects, "
              f"labels={a.deap_labels if name == 'DEAP' else 'DREAMER.mat'}  [{time.time()-t0:.0f}s]", flush=True)
        sid, chance = R.subject_id_acc(X, subj, trial)
        RES[name] = dict(n_windows=int(X.shape[0]), n_subjects=int(len(set(subj.tolist()))),
                         n_trials=int(len(np.unique(trial))),
                         label_source=(a.deap_labels if name == "DEAP" else "DREAMER.mat"),
                         subject_id_acc=sid, subject_id_chance=chance, schemes={})
        print(f"subject-identity decoding: {sid:.3f} (chance {chance:.3f})", flush=True)
        for sch_name, sch_fn in R.SCHEMES:
            RES[name]["schemes"][sch_name] = {}
            for tgt, r in [("valence", val), ("arousal", aro)]:
                y = sch_fn(r) if sch_name == "global_median" else sch_fn(r, subj)
                br = R.base_rate_spread(y, subj)
                cell = dict(pos_rate=float(y.mean()), base_rate=br, protocols={})
                print(f"--- {name}/{sch_name}/{tgt}: pos {y.mean():.3f}, base rate "
                      f"[{br['min']:.2f}, {br['max']:.2f}]", flush=True)
                for pname, fn in PROTOCOLS:
                    res = fn(X, y, subj, trial)
                    cell["protocols"][pname] = dict(auc=float(res["auc"]), ci=list(res["ci"]),
                                                    folds=res["folds"], unit=res["unit"],
                                                    n_scored=int(len(res["y"])))
                    np.savez_compressed(out / "oof" / f"{name}_{sch_name}_{tgt}_{pname}.npz",
                                        pred=res["pred"], y=res["y"], subj=res["subj"],
                                        trial=res["trial"], fold=res["fold"])
                    print(f"  {pname:38s} AUC {res['auc']:.3f} [{res['ci'][0]:.3f}, {res['ci'][1]:.3f}]"
                          f"  [{time.time()-t0:.0f}s]", flush=True)
                RES[name]["schemes"][sch_name][tgt] = cell

    RES["_manifest"] = dict(
        command=" ".join(sys.argv), deap_labels=a.deap_labels, runtime_s=round(time.time() - t0, 1),
        python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
        sklearn=sklearn.__version__, xgboost=xgboost.__version__, seed=R.SEED,
        git=git_state(),
        script_sha256={f: deap_labels.sha256(R.HERE / f) for f in
                       ["run_protocols.py", "rev1_protocols.py", "deap_labels.py"]},
        cache_sha256={n: deap_labels.sha256(R.CACHE / f"{n}.npz") for n in a.datasets},
        label_csv_sha256=deap_labels.sha256(deap_labels.CSV) if a.deap_labels == "corrected" else None)
    (out / "protocols.json").write_text(json.dumps(RES, indent=2))
    print(f"\nwrote {out/'protocols.json'} in {time.time()-t0:.0f}s", flush=True)

    if a.gate:
        sub = json.loads(SUBMITTED.read_text())
        sub = {k: v for k, v in sub.items() if k in a.datasets}
        diffs = compare(sub, RES)
        report = dict(submitted=str(SUBMITTED.resolve().relative_to((R.HERE / "..").resolve())),
                      tolerance=TOL, n_values_compared=count_numeric(sub),
                      n_differences=len(diffs),
                      differences=[dict(path=p, submitted=s, rerun=n) for p, s, n in diffs[:200]],
                      passed=len(diffs) == 0)
        (out / "gate_report.json").write_text(json.dumps(report, indent=2))
        print(f"GATE {'PASSED' if not diffs else 'FAILED'}: {len(diffs)} values differ by more than {TOL}")
        sys.exit(0 if not diffs else 1)
