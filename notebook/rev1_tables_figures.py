"""
Frontiers revision (rev1): LaTeX tables, CSV tables and figures from the E1 to E5 result files.

    python rev1_tables_figures.py
Writes results/rev1/tables/*.tex, *.csv and results/rev1/figures/*.pdf, *.png. Missing inputs are skipped.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REV1 = (Path(__file__).resolve().parent / "../results/rev1").resolve()
TAB = REV1 / "tables"; FIG = REV1 / "figures"
TAB.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
DATASETS, TARGETS, PROTOCOLS = ["DEAP", "DREAMER"], ["valence", "arousal"], ["P1", "P2", "P3", "P4"]
BLUE, ORANGE, AQUA, GREY, INK, MUTED = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984", "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8, "legend.fontsize": 7.5,
                     "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "axes.edgecolor": GREY, "axes.linewidth": 0.6,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.labelcolor": INK, "pdf.fonttype": 42})


def load(path):
    p = REV1 / path
    return json.loads(p.read_text()) if p.exists() else None


def f3(x):
    return f"{x:.3f}"


def aci(d, key="ci"):
    return f"{d['auc']:.3f} [{d[key][0]:.3f}, {d[key][1]:.3f}]"


def dci(d, key="ci"):
    return f"{d['diff']:+.3f} [{d[key][0]:+.3f}, {d[key][1]:+.3f}]"


import re as _re
_EST_CI = _re.compile(r"(?<![\w\[])([+-]?\d\.\d{3}) (\[[+-]?\d\.\d{3}, [+-]?\d\.\d{3}\])")


def _stack(line):
    """Put each interval under its estimate inside the cell, so wide tables fit the text width."""
    return _EST_CI.sub(lambda m: "\\begin{tabular}[t]{@{}c@{}}" + m.group(1) + "\\\\ {" + m.group(2) + "}\\end{tabular}", line)


def _stack_header(header):
    """Break long header labels (marked with ' / ') onto two lines."""
    cells = header.rstrip().removesuffix("\\\\").split(" & ")
    out = []
    for c in cells:
        c = c.strip()
        out.append("\\begin{tabular}[b]{@{}c@{}}" + c.replace(" / ", "\\\\ ") + "\\end{tabular}" if " / " in c else c)
    return " & ".join(out) + " \\\\"


def write_table(name, df, latex_body, caption, label, colspec, header):
    df.to_csv(TAB / f"{name}.csv", index=False)
    body = [_re.sub(r"(?<![\w$\-{])-(?=\d)", "$-$", _stack(l)) for l in latex_body]
    tex = ["\\begin{table}[htbp]", "\\centering\\scriptsize\\setlength{\\tabcolsep}{3pt}", f"\\caption{{{caption}}}", f"\\label{{{label}}}",
           "\\begin{adjustbox}{max width=\\textwidth}",
           f"\\begin{{tabular}}{{{colspec}}}", "\\toprule", _stack_header(header), "\\midrule", *body, "\\bottomrule",
           "\\end{tabular}", "\\end{adjustbox}", "\\end{table}"]
    (TAB / f"{name}.tex").write_text("\n".join(tex) + "\n")


# ------------------------------------------------------------------ Table: exact P1-P4 and contrasts (E1)
def table_protocols():
    rows, body = [], []
    for scheme, title in [("global", "Training-median labels (primary)"),
                          ("participant", "Per-participant-median labels (target-derived sensitivity analysis)")]:
        body.append(f"\\multicolumn{{8}}{{@{{}}l}}{{\\textit{{{title}}}}} \\\\")
        for ds in DATASETS:
            d = load(f"e1/{ds}_{scheme}.json")
            if d is None:
                continue
            for t in TARGETS:
                c = d["targets"][t]; P = c["protocols"]
                vals = [aci(P[p]["trial_level"]["eeg"]) for p in PROTOCOLS]
                con = [dci(c["contrasts"]["P1-P2"]), dci(c["contrasts"]["P2-P3"])]
                rows.append(dict(scheme=scheme, dataset=ds, target=t, **dict(zip(PROTOCOLS, vals)),
                                 **{"P1-P2": con[0], "P2-P3": con[1]},
                                 **{f"{p}_window": aci(P[p]["window_level"]["eeg"]) for p in PROTOCOLS}))
                body.append(f"{ds} & {t} & " + " & ".join(vals) + " & " + " & ".join(con) + " \\\\")
        body.append("\\addlinespace")
    write_table("table_protocols", pd.DataFrame(rows), body[:-1],
                "Exact four-protocol results on corrected DEAP labels. Trial-level AUC with 95\\% participant-bootstrap "
                "intervals (1,000 draws). P1, window-pooled 5-fold; P2, trial-grouped 5-fold with participants on both "
                "sides; P3, participant-grouped 5-fold; P4, leave-one-participant-out. The last two columns are paired "
                "differences. Window-level AUCs are given in Supplementary Table S2.",
                "tab:protocols", "@{}llcccccc@{}",
                "Dataset & Target & P1 & P2 & P3 & P4 & P1 $-$ P2 & P2 $-$ P3 \\\\")


# ------------------------------------------------------------------ Table: no-EEG baselines (E2)
def table_priors():
    rows, body = [], []
    for ds in DATASETS:
        d = load(f"e1/{ds}_global.json")
        if d is None:
            continue
        for t in TARGETS:
            c = d["targets"][t]
            for p in PROTOCOLS:
                tl = c["protocols"][p]["trial_level"]
                r = dict(dataset=ds, target=t, protocol=p, eeg=aci(tl["eeg"]),
                         participant_prior=aci(tl["prior_participant"]), stimulus_prior=aci(tl["prior_stimulus"]),
                         global_prior=f3(tl["prior_global"]["auc"]),
                         eeg_minus_participant_prior=dci(c["contrasts"][f"{p}: eeg-prior_participant"]))
                rows.append(r)
                lead = f"{ds} & {t}" if p == "P1" else " & "
                body.append(f"{lead} & {p} & {r['eeg']} & {r['participant_prior']} & {r['eeg_minus_participant_prior']} "
                            f"& {r['stimulus_prior']} & {r['global_prior']} \\\\")
            body.append("\\addlinespace")
    write_table("table_priors", pd.DataFrame(rows), body[:-1],
                "Baselines that use no EEG, on the folds and labels of Table~\\ref{tab:protocols} (training-median labels). "
                "Participant prior: the test participant's positive rate among the training trials, or the training rate "
                "when the participant is absent from training (P3, P4). Stimulus prior: the test clip's positive rate among "
                "the training trials. Global prior: one training positive rate per fold, a no-information reference whose "
                "pooled AUC departs from 0.5 because fold prevalences differ. Trial-level AUC with 95\\% participant-bootstrap "
                "intervals; EEG $-$ participant prior is paired.",
                "tab:priors", "@{}lllccccc@{}",
                "Dataset & Target & Protocol & EEG model & Participant / prior & EEG $-$ / participant prior & Stimulus / prior & Global prior / (reference) \\\\")


# ------------------------------------------------------------------ Table + figure: identity removal (E3)
def table_identity_removal():
    """Largest k per dataset (DEAP 24, DREAMER 16), with the identity manipulation check beside the emotion results."""
    ident = {}
    for ds in DATASETS:
        d = load(f"e3/{ds}_valence.json")
        if d and d.get("identity_check"):
            for p, lst in d["identity_check"].items():
                for c in lst:
                    ident.setdefault((ds, p, c["learner"], c["kind"], c["k"]), []).append(c["accuracy"])
    rows, body = [], []
    for ds in DATASETS:
        for t in TARGETS:
            d = load(f"e3/{ds}_{t}.json")
            if d is None:
                continue
            k = max(d["k_grid"])
            for L, lname in [("xgb", "XGBoost"), ("logreg", "Logistic")]:
                get = lambda p, kind, kk, dr: next(c for c in d["protocols"][p]["conditions"]
                                                   if c["learner"] == L and c["kind"] == kind and c["k"] == kk and c["draw"] == dr)
                con = next(c for c in d["contrasts"] if c["learner"] == L and c["k"] == k)
                id0 = ident.get((ds, "P2", L, "identity", 0)); idk = ident.get((ds, "P2", L, "identity", k))
                r = dict(dataset=ds, target=t, learner=lname, k=k,
                         identity_P2_before=None if id0 is None else float(np.mean(id0)),
                         identity_P2_after=None if idk is None else float(np.mean(idk)))
                for p in ["P2", "P3"]:
                    r[f"{p}_before"] = aci(get(p, "identity", 0, -1))
                    r[f"{p}_after"] = aci(get(p, "identity", k, -1))
                    r[f"{p}_change"] = dci(con[f"{p}: identity k - k0"])
                    r[f"{p}_identity_minus_random"] = dci(con[f"{p}: identity k - random k"])
                r["P2_change_minus_P3_change"] = dci(con["(P2 change) - (P3 change)"])
                rows.append(r)
                idtxt = "--" if id0 is None else f"{r['identity_P2_before']:.2f} $\\to$ {r['identity_P2_after']:.2f}"
                lead = f"{ds} & {t}" if L == "xgb" else " & "
                body.append(f"{lead} & {lname} & {k} & {idtxt} & {r['P2_before']} & {r['P2_change']} & {r['P3_before']} & "
                            f"{r['P3_change']} & {r['P2_change_minus_P3_change']} \\\\")
        body.append("\\addlinespace")
    if rows:
        write_table("table_identity_removal", pd.DataFrame(rows), body[:-1],
                    "Identity removal. Within each training fold the $k$ directions that best separate the training "
                    "participants (after within-participant whitening) are projected out and the fixed projection is applied "
                    "to the test trials. Identity: decoding accuracy for the same participants on held-out trials (P2, first "
                    "fold) before and after removal; chance is 0.03 on DEAP and 0.04 on DREAMER, and identity values are "
                    "shown once per dataset because they do not depend on the target. AUCs are trial-level with 95\\% "
                    "participant-bootstrap intervals before removal (whitened features), followed by the paired change after "
                    "removal and the difference between the P2 and P3 changes, which the identity account predicts to be "
                    "negative. Random-direction controls and intermediate $k$ are in Supplementary Table S3.",
                    "tab:identity_removal", "@{}lllccccccc@{}",
                    "Dataset & Target & Model & $k$ & Identity (P2) & P2 before & P2 change & P3 before & P3 change & P2 $-$ P3 change \\\\")
    mrows = [dict(dataset=k[0], protocol=k[1], learner=k[2], kind=k[3], k=k[4], accuracy=float(np.mean(v))) for k, v in ident.items()]
    if mrows:
        pd.DataFrame(mrows).sort_values(["dataset", "protocol", "learner", "kind", "k"]).to_csv(TAB / "table_identity_decodability.csv", index=False)


def figure_identity_removal():
    have = [(ds, t) for ds in DATASETS for t in TARGETS if (REV1 / f"e3/{ds}_{t}.json").exists()]
    if not have:
        return
    fig, axes = plt.subplots(2, 2, figsize=(6.7, 4.6), sharey=False)
    for ax, (ds, t) in zip(axes.flat, [(ds, t) for ds in DATASETS for t in TARGETS]):
        d = load(f"e3/{ds}_{t}.json")
        ax.set_title(f"{ds} {t}", loc="left", color=INK)
        if d is None:
            ax.axis("off"); continue
        for p, col, mk in [("P2", BLUE, "o"), ("P3", ORANGE, "s")]:
            C = pd.DataFrame(d["protocols"][p]["conditions"]); C = C[C.learner == "xgb"]
            idc = C[C.kind == "identity"].sort_values("k")
            rnd = C[C.kind == "random"].groupby("k").auc.mean().reindex(idc.k).fillna(idc.set_index("k").auc)
            lo = [c[0] for c in idc.ci]; hi = [c[1] for c in idc.ci]
            ax.fill_between(idc.k, lo, hi, color=col, alpha=0.12, lw=0)
            ax.plot(idc.k, idc.auc, color=col, lw=2, marker=mk, ms=4.5, label=f"{p}, identity directions removed")
            ax.plot(rnd.index, rnd.values, color=col, lw=1.2, ls=(0, (3, 2)), label=f"{p}, random directions removed")
        ax.axhline(0.5, color=GREY, lw=0.6, ls=":")
        ax.set_xlabel("directions removed (k)"); ax.set_ylabel("trial-level AUC")
        ax.grid(axis="y", color="#e6e5e1", lw=0.5); ax.set_axisbelow(True)
        for s in ["top", "right"]:
            ax.spines[s].set_visible(False)
    h, l = next((a.get_legend_handles_labels() for a in axes.flat if a.get_legend_handles_labels()[0]), ([], []))
    fig.legend(h, l, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    for ext in ["pdf", "png"]:
        fig.savefig(FIG / f"fig_identity_removal.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ Table: is identity used? (E1 + E3 + E3b)
def table_identity_use():
    rows, body = [], []
    for ds in DATASETS:
        e1 = load(f"e1/{ds}_global.json"); e3b = load(f"e3b/{ds}.json")
        if e1 is None or e3b is None:
            continue
        for t in TARGETS:
            c1 = e1["targets"][t]; dec = e3b["targets"][t]["decomposition"]; rw = e3b["targets"][t]["reweighting"]
            e3 = load(f"e3/{ds}_{t}.json")
            k = max(e3["k_grid"]) if e3 else None
            rm = next(c for c in e3["contrasts"] if c["learner"] == "xgb" and c["k"] == k) if e3 else None
            pp = c1["contrasts"]["P2: eeg-prior_participant"]
            r = dict(dataset=ds, target=t, overlap_gap=dci(c1["contrasts"]["P2-P3"]),
                     eeg_minus_participant_prior_P2=dci(pp),
                     gap_within=dci(dec["P2-P3 eeg within"]), gap_between=dci(dec["P2-P3 eeg between"]),
                     P4_within_participant_auc=aci(dict(auc=dec["P4/eeg"]["within"]["auc"], ci=dec["P4/eeg"]["within"]["ci"])),
                     reweighting_P2_change=dci(rw["P2"]["balanced-unweighted"]),
                     reweighting_P2_minus_P3_change=dci(rw["(P2 change) - (P3 change)"]),
                     removal_P2_minus_P3_change=None if rm is None else dci(rm["(P2 change) - (P3 change)"]), removal_k=k)
            rows.append(r)
            body.append(f"{ds} & {t} & {r['overlap_gap']} & {r['eeg_minus_participant_prior_P2']} & {r['gap_within']} & {r['gap_between']} & "
                        f"{r['reweighting_P2_minus_P3_change']} & {r['removal_P2_minus_P3_change']} \\\\")
    if rows:
        write_table("table_identity_use", pd.DataFrame(rows), body,
                    "Is participant identity used? All entries are paired differences in trial-level AUC with 95\\% "
                    "participant-bootstrap intervals, training-median labels. Overlap gap: P2 $-$ P3. EEG $-$ prior: the EEG "
                    "model minus the no-EEG participant prior under P2. Within and between: the P2 $-$ P3 gap computed only "
                    "over pairs of trials from the same participant, or only over pairs from different participants. "
                    "Reweighting: change in the overlap gap when training weights balance the classes within each participant. "
                    "Removal: change in the overlap gap when the $k$ most identity-discriminative directions are projected out "
                    "(XGBoost; $k$ = 24 on DEAP, 16 on DREAMER). If the advantage runs through participant label tendencies, "
                    "the between-participant gap carries it and reweighting and removal are negative.",
                    "tab:identity_use", "@{}llcccccc@{}",
                    "Dataset & Target & Overlap gap / (P2 $-$ P3) & EEG $-$ prior / (P2) & Gap within / participants & Gap between / participants & Reweighting / change in gap & Removal / change in gap \\\\")


# ------------------------------------------------------------------ Table: normalization (E4)
ARM_LABEL = {"none": "None (reference)", "A": "Global, training rows", "D": "Global, all rows incl. test$^{\\dagger}$",
             "B": "Per participant, calibration trials$^{\\ddagger}$", "C": "Per participant, whole recording$^{\\dagger}$"}


def table_normalization():
    rows, body = [], []
    for ds in DATASETS:
        for t in TARGETS:
            d = load(f"e4/{ds}_{t}.json")
            if d is None:
                continue
            for arm in ["A", "B", "C", "D", "none"]:
                x = d["arms"]["xgb"][arm]; lg = d["arms"]["logreg"][arm]
                dx = "reference" if arm == "A" else dci(d["contrasts"]["xgb"][f"{arm}-A"])
                dl = "reference" if arm == "A" else dci(d["contrasts"]["logreg"][f"{arm}-A"])
                r = dict(dataset=ds, target=t, arm=arm, leakage=d["leakage"][arm], xgb=aci(x), xgb_delta=dx,
                         xgb_within=f3(x["within_participant_auc"]), logreg=aci(lg), logreg_delta=dl)
                rows.append(r)
                lead = f"{ds} & {t}" if arm == "A" else " & "
                body.append(f"{lead} & {ARM_LABEL[arm]} & {r['xgb']} & {dx} & {r['logreg']} & {dl} \\\\")
            body.append("\\addlinespace")
    if rows:
        write_table("table_normalization", pd.DataFrame(rows), body[:-1],
                    "Normalization scope under leave-one-participant-out evaluation. Feature-level z-scoring; the same "
                    "scored trials in every arm (calibration trials excluded from training and scoring throughout). "
                    "Trial-level AUC with 95\\% participant-bootstrap intervals; $\\Delta$ is the paired difference from "
                    "training-rows global normalization. $^{\\dagger}$Transductive: statistics include the held-out "
                    "participant's scored feature data (no labels). $^{\\ddagger}$Uses the held-out participant's unlabelled "
                    "calibration trials but not the scored trials.",
                    "tab:normalization", "@{}lllcccc@{}",
                    "Dataset & Target & Normalization & XGBoost & $\\Delta$ from / training-only & Logistic / regression & $\\Delta$ from / training-only \\\\")


# ------------------------------------------------------------------ Table: stimulus control (E5)
def stimulus_average(ds, t, RC, Dp, Sv):
    """Seen- versus unseen-stimulus AUC with window-averaged trial scores averaged over the block assignments."""
    T = pd.concat([pd.read_parquet(f) for f in sorted(REV1.glob(f"e5/oof/{ds}_{t}_seed*_trials.parquet"))])
    A = (T.groupby(["arm", "trial"]).agg(subj=("subj", "first"), stim=("stim", "first"), y=("y", "mean"),
                                         eeg=("eeg", "mean"), prior_stimulus=("prior_stimulus", "mean")).reset_index())
    mixed = int(((A.y > 0) & (A.y < 1)).sum()); A["y"] = (A.y >= 0.5).astype(int)
    est, boots = {}, {}
    for arm in ["US", "UU"]:
        g = A[A.arm == arm].sort_values("trial")
        y, sj, st = g.y.to_numpy(), g.subj.to_numpy(), g.stim.to_numpy()
        for sc in ["eeg", "prior_stimulus"]:
            summ, b = RC.summarize(y, g[sc].to_numpy(), sj, Dp)
            bx = RC.boot_aucs(y, g[sc].to_numpy(), sj, Dp, st, Sv)
            summ["ci_crossed"] = RC.ci(bx); est[(arm, sc)] = summ; boots[(arm, sc)] = (b, bx)
    d = est[("US", "eeg")]["auc"] - est[("UU", "eeg")]["auc"]
    dif = dict(diff=d, ci=RC.ci(boots[("US", "eeg")][0] - boots[("UU", "eeg")][0]),
               ci_crossed=RC.ci(boots[("US", "eeg")][1] - boots[("UU", "eeg")][1]))
    seeds = [json.loads(f.read_text())["targets"][t]["contrasts"]["eeg: US-UU"]["diff"] for f in sorted(REV1.glob(f"e5/{ds}_seed*.json"))]
    return est, dif, seeds, mixed


def table_stimulus():
    """Primary estimate: window-averaged trial scores averaged over the five block assignments, per arm."""
    import rev1_common as RC
    rows, body = [], []
    for ds in DATASETS:
        files = sorted(REV1.glob(f"e5/oof/{ds}_valence_seed*_trials.parquet"))
        if len(files) < 5:
            continue
        D = RC.load(ds); Dp = RC.draws(D["subj"]); Sv = RC.stim_draws(D["stim"])
        for t in TARGETS:
            est, dif, seeds, mixed = stimulus_average(ds, t, RC, Dp, Sv)
            r = dict(dataset=ds, target=t, seen_stimulus=aci(est[("US", "eeg")]), unseen_stimulus=aci(est[("UU", "eeg")]),
                     difference=dci(dif), difference_ci_crossed=f"[{dif['ci_crossed'][0]:+.3f}, {dif['ci_crossed'][1]:+.3f}]",
                     difference_range_over_assignments=f"{min(seeds):+.3f} to {max(seeds):+.3f}",
                     stimulus_prior_seen=aci(est[("US", "prior_stimulus")]), stimulus_prior_unseen=f3(est[("UU", "prior_stimulus")]["auc"]),
                     trials_with_mixed_labels_across_assignments=mixed)
            rows.append(r)
            body.append(f"{ds} & {t} & {r['seen_stimulus']} & {r['unseen_stimulus']} & {r['difference']} & "
                        f"{r['difference_ci_crossed']} & {r['difference_range_over_assignments']} & {r['stimulus_prior_seen']} \\\\")
    if rows:
        write_table("table_stimulus", pd.DataFrame(rows), body,
                    "Unseen participants with seen versus unseen stimuli in the size-matched participant-block $\\times$ "
                    "stimulus-block design (DEAP 8 $\\times$ 5, DREAMER 6 $\\times$ 6). Both arms train on the same "
                    "participants and on the same number of trials and clips, and differ only in whether the test clips were "
                    "seen through other participants. Trial scores are averaged over five random block assignments; "
                    "trial-level AUC with 95\\% participant-bootstrap intervals. The difference (seen $-$ unseen) is paired, "
                    "with a crossed participant $\\times$ clip bootstrap interval and the range of the difference over the "
                    "individual assignments. Stimulus prior: the no-EEG clip positive rate in the seen-stimulus arm.",
                    "tab:stimulus", "@{}llcccccc@{}",
                    "Dataset & Target & Seen / stimulus & Unseen / stimulus & Difference / (seen $-$ unseen) & Crossed / interval & Range over / assignments & Stimulus prior / (seen) \\\\")


# ------------------------------------------------------------------ Table: external test on FACED
def table_faced():
    import rev1_common as RC
    e1 = load("e1/FACED_global.json"); e3b = load("e3b/FACED.json")
    if e1 is None or e3b is None or len(list(REV1.glob("e5/oof/FACED_valence_seed*_trials.parquet"))) < 5:
        return
    D = RC.load("FACED"); Dp = RC.draws(D["subj"]); Sv = RC.stim_draws(D["stim"])
    rows = {}
    for t in TARGETS:
        c = e1["targets"][t]; P = c["protocols"]; dec = e3b["targets"][t]["decomposition"]; rw = e3b["targets"][t]["reweighting"]
        est, dif, seeds, _ = stimulus_average("FACED", t, RC, Dp, Sv)
        rows[t] = [
            ("P1, window-pooled", aci(P["P1"]["trial_level"]["eeg"])),
            ("P2, trial-grouped", aci(P["P2"]["trial_level"]["eeg"])),
            ("P2B, presentation-block-grouped", aci(P["P2B"]["trial_level"]["eeg"])),
            ("P3, participant-grouped", aci(P["P3"]["trial_level"]["eeg"])),
            ("P4, leave-one-participant-out", aci(P["P4"]["trial_level"]["eeg"])),
            ("P4, within-participant AUC", aci(dict(auc=dec["P4/eeg"]["within"]["auc"], ci=dec["P4/eeg"]["within"]["ci"]))),
            ("Participant prior, no EEG (P2)", aci(P["P2"]["trial_level"]["prior_participant"])),
            ("Stimulus prior, no EEG (P2)", aci(P["P2"]["trial_level"]["prior_stimulus"])),
            ("EEG $-$ participant prior (P2)", dci(c["contrasts"]["P2: eeg-prior_participant"])),
            ("Correlated-window step, P1 $-$ P2", dci(c["contrasts"]["P1-P2"])),
            ("Participant-overlap step, P2 $-$ P3", dci(c["contrasts"]["P2-P3"])),
            ("Participant-overlap step, P2B $-$ P3", dci(c["contrasts"]["P2B-P3"])),
            ("Overlap gap within participants", dci(dec["P2-P3 eeg within"])),
            ("Overlap gap between participants", dci(dec["P2-P3 eeg between"])),
            ("Reweighting, change in overlap gap", dci(rw["(P2 change) - (P3 change)"])),
            ("Seen $-$ unseen stimulus (5 assignments)", dci(dif)),
        ]
    body = [f"{name} & {rows['valence'][i][1]} & {rows['arousal'][i][1]} \\\\" for i, (name, _) in enumerate(rows["valence"])]
    ip = e1["identity_probe"]
    body.append(f"Identity decoding, window accuracy (chance {ip['chance']:.3f}) & \\multicolumn{{2}}{{c}}{{{ip['accuracy']:.3f}}} \\\\")
    df = pd.DataFrame([dict(analysis=rows["valence"][i][0], valence=rows["valence"][i][1], arousal=rows["arousal"][i][1])
                       for i in range(len(rows["valence"]))] + [dict(analysis="identity decoding accuracy", valence=ip["accuracy"], arousal=ip["accuracy"])])
    write_table("table_faced", df, body,
                "External test on FACED (123 participants, 28 clips, ratings on continuous 0 to 7 scales; Fp1 and Fp2 in place "
                "of AF3 and AF4; 30 s trials). Training-median labels. Trial-level AUC or paired difference with 95\\% "
                "participant-bootstrap intervals. P2B holds out whole presentation blocks of four same-valence clips while "
                "keeping participants on both sides. The analyses follow Tables~\\ref{tab:protocols} to~\\ref{tab:stimulus}.",
                "tab:faced", "@{}lcc@{}", "Analysis & Valence & Arousal \\\\")


# ------------------------------------------------------------------ Supplementary tables S2, S3
def supp_window_level():
    rows, body = [], []
    have = [d for d in DATASETS + ["FACED"] if (REV1 / f"e1/{d}_global.json").exists()]
    for scheme in ["global", "participant"]:
        for ds in have:
            d = load(f"e1/{ds}_{scheme}.json")
            if d is None:
                continue
            for t in TARGETS:
                c = d["targets"][t]; P = c["protocols"]
                seeds = {p: [P[p]["trial_level"]["eeg"]["auc"]] + [c["partition_seeds"][k][p] for k in c["partition_seeds"]] for p in ["P1", "P2", "P3"]}
                r = dict(scheme=scheme, dataset=ds, target=t, **{f"{p}_window": aci(P[p]["window_level"]["eeg"]) for p in PROTOCOLS},
                         **{f"{p}_trial_range_5_partitions": f"{min(v):.3f}--{max(v):.3f}" for p, v in seeds.items()})
                rows.append(r)
                lab = "training median" if scheme == "global" else "participant median"
                body.append(f"{lab} & {ds} & {t} & " + " & ".join(r[f'{p}_window'] for p in PROTOCOLS) + " & " +
                            " & ".join(r[f'{p}_trial_range_5_partitions'] for p in ["P1", "P2", "P3"]) + " \\\\")
    write_table("supp_S2_window_level", pd.DataFrame(rows), body,
                "Window-level AUC (window probabilities scored individually) with 95\\% participant-bootstrap intervals, and "
                "the range of trial-level AUC over five fold partitions (the primary seed and four further seeds) for P1 to P3. "
                "P4 has a single partition.", "tab:S2", "@{}lllccccccc@{}",
                "Labels & Dataset & Target & P1 & P2 & P3 & P4 & P1 range & P2 range & P3 range \\\\")


def supp_identity_removal():
    rows = []
    ident = {}
    for ds in DATASETS:
        d = load(f"e3/{ds}_valence.json")
        if d and d.get("identity_check"):
            for p, lst in d["identity_check"].items():
                for c in lst:
                    ident.setdefault((ds, p, c["learner"], c["kind"], c["k"]), []).append(c["accuracy"])
    body = []
    for ds in DATASETS:
        for t in TARGETS:
            d = load(f"e3/{ds}_{t}.json")
            if d is None:
                continue
            for L, lname in [("xgb", "XGBoost"), ("logreg", "Logistic")]:
                for k in d["k_grid"]:
                    r = dict(dataset=ds, target=t, learner=lname, k=k)
                    for p in ["P2", "P3"]:
                        C = [c for c in d["protocols"][p]["conditions"] if c["learner"] == L and c["k"] == k]
                        idc = next(c for c in C if c["kind"] == "identity")
                        rnd = [c["auc"] for c in C if c["kind"] == "random"]
                        r[f"{p}_identity_removed"] = aci(idc)
                        r[f"{p}_random_removed_mean"] = f3(np.mean(rnd)) if rnd else "--"
                        acc = ident.get((ds, p, L, "identity", k)); racc = ident.get((ds, p, L, "random", k))
                        r[f"{p}_identity_decoding_after_identity_removal"] = f"{np.mean(acc):.2f}" if acc else "--"
                        r[f"{p}_identity_decoding_after_random_removal"] = f"{np.mean(racc):.2f}" if racc else "--"
                    rows.append(r)
                    body.append(f"{ds} & {t} & {lname} & {k} & {r['P2_identity_removed']} & {r['P2_random_removed_mean']} & "
                                f"{r['P2_identity_decoding_after_identity_removal']} / {r['P2_identity_decoding_after_random_removal']} & "
                                f"{r['P3_identity_removed']} & {r['P3_random_removed_mean']} & "
                                f"{r['P3_identity_decoding_after_identity_removal']} / {r['P3_identity_decoding_after_random_removal']} \\\\")
            body.append("\\addlinespace")
    if rows:
        write_table("supp_S3_identity_removal", pd.DataFrame(rows), body[:-1],
                    "Identity removal for every $k$. AUC: trial-level with 95\\% participant-bootstrap interval after removing the $k$ "
                    "most identity-discriminative directions; Random: mean AUC after removing $k$ random orthonormal directions (two "
                    "draws). Identity decoding (first fold, identity removal / random removal): P2, the same participants on unseen "
                    "trials (chance 0.03 DEAP, 0.04 DREAMER); P3, among the held-out participants only, with a transform fitted without "
                    "them (chance 0.14 to 0.20). $k = 0$ is the whitened representation with nothing removed.",
                    "tab:S3", "@{}llllcccccc@{}",
                    "Dataset & Target & Model & $k$ & P2 AUC & P2 random & P2 identity & P3 AUC & P3 random & P3 identity \\\\")


# ------------------------------------------------------------------ Figure: main performance (E1 + E2)
def figure_performance():
    dsets = [d for d in DATASETS + ["FACED"] if (REV1 / f"e1/{d}_global.json").exists()]
    fig, axes = plt.subplots(len(dsets), 2, figsize=(6.7, 2.4 * len(dsets)), sharey=True)
    x = np.arange(4)
    for ax, (ds, t) in zip(axes.flat, [(ds, t) for ds in dsets for t in TARGETS]):
        ax.set_title(f"{ds} {t}", loc="left", color=INK)
        d = load(f"e1/{ds}_global.json")
        if d is None:
            ax.axis("off"); continue
        P = d["targets"][t]["protocols"]
        for s, col, mk, off, lab in [("eeg", BLUE, "o", -0.18, "EEG model (XGBoost)"),
                                      ("prior_participant", ORANGE, "s", 0.0, "Participant prior (no EEG)"),
                                      ("prior_stimulus", AQUA, "^", 0.18, "Stimulus prior (no EEG)")]:
            auc = np.array([P[p]["trial_level"][s]["auc"] for p in PROTOCOLS])
            lo = np.array([P[p]["trial_level"][s]["ci"][0] for p in PROTOCOLS])
            hi = np.array([P[p]["trial_level"][s]["ci"][1] for p in PROTOCOLS])
            ax.errorbar(x + off, auc, yerr=[auc - lo, hi - auc], fmt=mk, color=col, ms=5.5, lw=1.4, capsize=0,
                        mec="white", mew=0.6, label=lab, zorder=3)
        ref = [P[p]["trial_level"]["prior_global"]["auc"] for p in PROTOCOLS]
        ax.hlines(ref, x - 0.32, x + 0.32, color=GREY, lw=1.2, label="No-information reference", zorder=2)
        ax.axhline(0.5, color=GREY, lw=0.6, ls=":", zorder=1)
        ax.set_xticks(x, PROTOCOLS)
        ax.set_ylim(0.25, 1.0); ax.set_ylabel("trial-level AUC")
        ax.grid(axis="y", color="#e6e5e1", lw=0.5); ax.set_axisbelow(True)
        for sp in ["top", "right"]:
            ax.spines[sp].set_visible(False)
    h, l = next((a.get_legend_handles_labels() for a in axes.flat if a.get_legend_handles_labels()[0]), ([], []))
    fig.legend(h, l, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.07 * 2 / len(dsets)))
    for ext in ["pdf", "png"]:
        fig.savefig(FIG / f"fig_performance.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    for fn in [table_faced, supp_window_level, supp_identity_removal, table_protocols, table_priors, table_identity_use, table_identity_removal, table_normalization, table_stimulus,
               figure_performance, figure_identity_removal]:
        try:
            fn(); print("ok", fn.__name__)
        except Exception as e:
            print("skipped", fn.__name__, type(e).__name__, e)
