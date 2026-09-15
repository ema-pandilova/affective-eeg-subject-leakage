"""
E0 (Frontiers revision): descriptive statistics computed in this article's own pipeline, on corrected DEAP labels.

1. Feature variance explained by participant: for each of the 66 features, one-way ANOVA eta squared of the
   trial-level feature means with participant as the factor; reported as the median (and IQR) over features.
   Trial means are used so that correlated windows are not counted as independent observations.
2. Rating variance explained by participant and by stimulus: one-way eta squared of the trial ratings with
   participant, and separately with stimulus (clip), as the factor.
3. Per-participant positive rates under the full-data median threshold (descriptive only; the evaluation
   protocols threshold on training data).

    python rev1_e0_descriptives.py
"""
from __future__ import annotations
import numpy as np, pandas as pd
import rev1_common as C


def eta2(values, groups):
    v = pd.Series(values); g = v.groupby(groups)
    grand = v.mean()
    ss_between = (g.count() * (g.mean() - grand) ** 2).sum()
    ss_total = ((v - grand) ** 2).sum()
    return float(ss_between / ss_total) if ss_total > 0 else float("nan")


if __name__ == "__main__":
    res = {}
    for name in ["DEAP", "DREAMER"]:
        D = C.load(name)
        df = pd.DataFrame(D["X"]); df["trial"] = D["trial"]
        T = df.groupby("trial").mean()
        meta = pd.DataFrame(dict(trial=D["trial"], subj=D["subj"], stim=D["stim"],
                                 valence=D["ratings"]["valence"], arousal=D["ratings"]["arousal"])).groupby("trial").first()
        T = T.loc[meta.index]
        feat = np.array([eta2(T[c].to_numpy(), meta.subj.to_numpy()) for c in range(D["X"].shape[1])])
        out = dict(feature_eta2_participant=dict(median=float(np.median(feat)), q25=float(np.percentile(feat, 25)),
                                                 q75=float(np.percentile(feat, 75)), n_features=int(len(feat)),
                                                 unit="trial-level feature means"))
        for t in C.TARGETS:
            r = meta[t].to_numpy()
            y = (r >= np.median(r)).astype(int)
            rates = pd.Series(y).groupby(meta.subj.to_numpy()).mean()
            out[t] = dict(rating_eta2_participant=eta2(r, meta.subj.to_numpy()),
                          rating_eta2_stimulus=eta2(r, meta.stim.to_numpy()),
                          full_data_median=float(np.median(r)), positive_rate=float(y.mean()),
                          participant_positive_rate_min=float(rates.min()), participant_positive_rate_max=float(rates.max()))
        res[name] = out
        print(name, out, flush=True)
    res["_manifest"] = C.manifest("rev1_e0_descriptives.py")
    C.dump(res, C.OUT / "e0_descriptives.json")
