"""
Frontiers revision (rev1): what the DEAP label correction changes in the submitted manuscript.

Inputs (both produced by rev1_protocols.py, identical code, differing only in the DEAP label source):
    results/rev1/gate_dat/     submission reproduced with the .dat labels (gate must have passed)
    results/rev1/corrected/    official DEAP ratings
Outputs:
    results/rev1/label_correction_diff.json
    results/rev1/LABEL_CORRECTION.md       before/after table and a verdict on every affected sentence

Protocol contrasts use a paired participant bootstrap: each draw resamples participants with replacement
and scores both protocols on the same resampled participants. The draws are generated exactly as in
run_protocols.boot_ci_subject (same generator, seed and call sequence), so the marginal intervals match
the ones in protocols.json, and the draw matrix is saved for reuse by later revision analyses.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score
import run_protocols as R
from deap_labels import sha256
from rev1_provenance import git_state

REV1 = (R.HERE / "../results/rev1").resolve()
P = ["P1_window_pooled", "P2_trial_grouped_participant_pooled", "P3_subject_grouped_windows", "P4_loso_trial"]
SHORT = dict(zip(P, ["P1", "P2", "P3", "P4"]))
N_BOOT = 1000


def draws_for(subs):
    rng = np.random.default_rng(R.SEED)
    return np.stack([rng.choice(subs, len(subs), replace=True) for _ in range(N_BOOT)])


def load_oof(tag, ds, sch, tgt, p):
    z = np.load(REV1 / tag / "oof" / f"{ds}_{sch}_{tgt}_{p}.npz", allow_pickle=True)
    return {k: z[k] for k in z.files}


def boot_aucs(o, draws):
    by = {s: np.where(o["subj"] == s)[0] for s in np.unique(o["subj"])}
    return np.array([roc_auc_score(o["y"][idx], o["pred"][idx])
                     for idx in (np.concatenate([by[s] for s in d]) for d in draws)])


def contrasts(tag, ds, sch, tgt, draws):
    oo = {p: load_oof(tag, ds, sch, tgt, p) for p in P[:3]}
    assert all(np.array_equal(oo[P[0]]["y"], oo[p]["y"]) and np.array_equal(oo[P[0]]["subj"], oo[p]["subj"])
               for p in P[1:3]), "P1-P3 must score the same rows"
    b = {p: boot_aucs(oo[p], draws) for p in P[:3]}
    point = {p: roc_auc_score(oo[p]["y"], oo[p]["pred"]) for p in P[:3]}
    pct = lambda d: [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]
    out = {}
    for a, c in [(P[0], P[1]), (P[1], P[2])]:
        out[f"{SHORT[a]}-{SHORT[c]}"] = dict(diff=float(point[a] - point[c]), ci=pct(b[a] - b[c]))
    # is the participant-overlap step larger than the correlated-window step?
    out["(P2-P3)-(P1-P2)"] = dict(diff=float((point[P[1]] - point[P[2]]) - (point[P[0]] - point[P[1]])),
                                  ci=pct((b[P[1]] - b[P[2]]) - (b[P[0]] - b[P[1]])))
    return out


def ci_str(ci):
    return f"[{ci[0]:.3f}, {ci[1]:.3f}]"


if __name__ == "__main__":
    gate = json.loads((REV1 / "gate_dat/gate_report.json").read_text())
    assert gate["passed"], "reproduction gate did not pass; refusing to build the disclosure table"
    old = json.loads((REV1 / "gate_dat/protocols.json").read_text())
    new = json.loads((REV1 / "corrected/protocols.json").read_text())

    res = dict(git=git_state(), gate=dict(passed=gate["passed"], n_values_compared=gate["n_values_compared"]),
               script_sha256={f: sha256(R.HERE / f) for f in
                              ["run_protocols.py", "rev1_protocols.py", "deap_labels.py", "rev1_label_diff.py"]},
               cells={}, binary_label_flips={})
    for ds in ["DEAP", "DREAMER"]:
        subs = np.unique(load_oof("corrected", ds, "global_median", "valence", P[0])["subj"])
        draws = draws_for(subs)
        np.save(REV1 / f"bootstrap_participant_draws_{ds}.npy", draws)
        for sch in ["global_median", "subject_median"]:
            for tgt in ["valence", "arousal"]:
                row = {}
                for lab, J, tag in [("submitted", old, "gate_dat"), ("corrected", new, "corrected")]:
                    c = J[ds]["schemes"][sch][tgt]
                    row[lab] = dict(pos_rate=c["pos_rate"], base_rate_min=c["base_rate"]["min"],
                                    base_rate_max=c["base_rate"]["max"],
                                    auc={SHORT[p]: c["protocols"][p]["auc"] for p in P},
                                    ci={SHORT[p]: c["protocols"][p]["ci"] for p in P},
                                    contrasts=contrasts(tag, ds, sch, tgt, draws))
                res["cells"][f"{ds}/{sch}/{tgt}"] = row
        for sch in ["global_median", "subject_median"]:
            for tgt in ["valence", "arousal"]:
                a_, b_ = (load_oof(t, ds, sch, tgt, P[3]) for t in ["gate_dat", "corrected"])
                assert np.array_equal(a_["trial"], b_["trial"])
                res["binary_label_flips"][f"{ds}/{sch}/{tgt}"] = dict(
                    trials=int((a_["y"] != b_["y"]).sum()), of=int(len(a_["y"])))
        res[f"{ds}_subject_id_acc"] = dict(submitted=old[ds]["subject_id_acc"], corrected=new[ds]["subject_id_acc"])

    C = res["cells"]
    def rng(lab, prots, sch="global_median"):
        v = [C[f"{d}/{sch}/{t}"][lab]["auc"][p] for d in ["DEAP", "DREAMER"] for t in ["valence", "arousal"] for p in prots]
        return [min(v), max(v)]
    def excl(lab, key, p):
        lo, hi = C[key][lab]["ci"][p]; return lo > 0.5 or hi < 0.5

    claims = []
    claims.append(dict(
        where="Abstract (TEX:36) and Section 4 (TEX:109)",
        text="a small transferable arousal effect remains on DEAP",
        submitted={f"{s}/{p}": [C[f'DEAP/{s}/arousal']['submitted']['auc'][p], C[f'DEAP/{s}/arousal']['submitted']['ci'][p]]
                   for s in ["global_median", "subject_median"] for p in ["P3", "P4"]},
        corrected={f"{s}/{p}": [C[f'DEAP/{s}/arousal']['corrected']['auc'][p], C[f'DEAP/{s}/arousal']['corrected']['ci'][p]]
                   for s in ["global_median", "subject_median"] for p in ["P3", "P4"]},
        corrected_valence_leakfree={f"{s}/{p}": [C[f'DEAP/{s}/valence']['corrected']['auc'][p], C[f'DEAP/{s}/valence']['corrected']['ci'][p]]
                                    for s in ["global_median", "subject_median"] for p in ["P3", "P4"]}))
    claims.append(dict(
        where="Section 3.4 (TEX:88)", text="per-subject positive rates on DEAP spread from 0.28 to 1.00",
        submitted={t: [C[f"DEAP/global_median/{t}"]["submitted"]["base_rate_min"], C[f"DEAP/global_median/{t}"]["submitted"]["base_rate_max"]] for t in ["valence", "arousal"]},
        corrected={t: [C[f"DEAP/global_median/{t}"]["corrected"]["base_rate_min"], C[f"DEAP/global_median/{t}"]["corrected"]["base_rate_max"]] for t in ["valence", "arousal"]}))
    claims.append(dict(
        where="Section 4 (TEX:107)", text="window pooling ... about 0.70 to 0.84",
        submitted=rng("submitted", ["P1"]), corrected=rng("corrected", ["P1"])))
    claims.append(dict(
        where="Section 4 (TEX:107)", text="trials grouped and participants held out ... about 0.46 to 0.55",
        submitted=rng("submitted", ["P3", "P4"]), corrected=rng("corrected", ["P3", "P4"])))
    claims.append(dict(
        where="Section 4 (TEX:107)",
        text="participant overlap is the larger contribution on DEAP, correlated windows on DREAMER; both are substantial",
        contrasts={k: {lab: C[k][lab]["contrasts"] for lab in ["submitted", "corrected"]}
                   for k in C if "/global_median/" in k}))
    claims.append(dict(
        where="Section 3.4 (TEX:88) and Section 4 (TEX:109)",
        text="per-subject-median labels remove almost all of the advantage that participant overlap confers",
        p2_minus_p3={k: {lab: C[k][lab]["contrasts"]["P2-P3"] for lab in ["submitted", "corrected"]} for k in C}))
    def leakfree_excluding_chance(lab, tgt):
        return [f"{s}/{p}" for s in ["global_median", "subject_median"] for p in ["P3", "P4"]
                if excl(lab, f"DEAP/{s}/{tgt}", p)]
    ab = leakfree_excluding_chance("corrected", "arousal")
    abv = [k for k in ab if C[f"DEAP/{k.split('/')[0]}/arousal"]["corrected"]["ci"][k.split('/')[1]][0] > 0.5]
    claims[0]["verdict"] = ("FALSE: no corrected DEAP arousal leak-free cell has an interval above 0.50"
                            if not abv else f"HOLDS in {abv}")
    claims[0]["corrected_valence_cells_above_chance"] = [
        k for k in leakfree_excluding_chance("corrected", "valence")
        if C[f"DEAP/{k.split('/')[0]}/valence"]["corrected"]["ci"][k.split('/')[1]][0] > 0.5]
    claims[1]["verdict"] = "NEW NUMBERS"
    r2 = lambda v: [round(v[0], 2), round(v[1], 2)]
    for i, stated in [(2, [0.70, 0.84]), (3, [0.46, 0.55])]:
        claims[i]["verdict"] = "HOLDS" if r2(claims[i]["corrected"]) == stated else \
            f"NEW NUMBERS: about {r2(claims[i]['corrected'])[0]:.2f} to {r2(claims[i]['corrected'])[1]:.2f}"
    v4 = {}
    for k in C:
        if "/global_median/" in k:
            cc = C[k]["corrected"]["contrasts"]
            lo, hi = cc["(P2-P3)-(P1-P2)"]["ci"]
            v4[k] = ("participant overlap larger" if lo > 0 else "correlated windows larger" if hi < 0
                     else "not distinguishable") + ("; P2-P3 interval includes 0" if cc["P2-P3"]["ci"][0] <= 0 else "")
    claims[4]["verdict"] = v4
    v5 = {}
    for ds in ["DEAP", "DREAMER"]:
        for tgt in ["valence", "arousal"]:
            g = C[f"{ds}/global_median/{tgt}"]["corrected"]["contrasts"]["P2-P3"]
            sm = C[f"{ds}/subject_median/{tgt}"]["corrected"]["contrasts"]["P2-P3"]
            if g["ci"][0] <= 0:
                v5[f"{ds}/{tgt}"] = "no participant-overlap advantage under global-median labels to remove"
            else:
                v5[f"{ds}/{tgt}"] = (f"{100 * (1 - sm['diff'] / g['diff']):.0f}% removed; residual "
                                     f"{'excludes' if sm['ci'][0] > 0 else 'includes'} 0")
    claims[5]["verdict"] = v5
    res["claims"] = claims
    (REV1 / "label_correction_diff.json").write_text(json.dumps(res, indent=2))

    # ---------------------------------------------------------------- markdown
    L = ["# DEAP label correction: before and after", "",
         "Generated by `notebook/rev1_label_diff.py`. \"Submitted\" is the submission reproduced by "
         f"`rev1_protocols.py --deap-labels dat` (reproduction gate passed on {gate['n_values_compared']} values, "
         "tolerance 5e-4). \"Corrected\" is the same code with the official DEAP ratings. DREAMER is unaffected and is "
         "shown only for the cross-dataset statements. AUC with 95% participant-bootstrap intervals; contrasts use a "
         "paired participant bootstrap (1,000 draws).", "",
         f"Code commit `{res['git']['commit'][:12]}` on branch `{res['git']['branch']}`; pipeline files "
         f"{'identical to that commit' if res['git']['pipeline_files_clean'] else 'MODIFIED: ' + ', '.join(res['git']['dirty_pipeline_files'])}. "
         "Full provenance in `PROVENANCE.json`.", "",
         "## Four-protocol AUC", "",
         "| Cell | Labels | pos. rate | base-rate range | P1 | P2 | P3 | P4 |", "|---|---|---|---|---|---|---|---|"]
    for k, row in C.items():
        for lab in ["submitted", "corrected"]:
            if k.startswith("DREAMER") and lab == "submitted":
                continue
            r = row[lab]
            L.append(f"| {k} | {lab if k.startswith('DEAP') else 'unchanged'} | {r['pos_rate']:.3f} | "
                     f"{r['base_rate_min']:.3f}-{r['base_rate_max']:.3f} | " +
                     " | ".join(f"{r['auc'][p]:.3f} {ci_str(r['ci'][p])}" for p in ["P1", "P2", "P3", "P4"]) + " |")
    L += ["", "## Protocol contrasts (paired participant bootstrap)", "",
          "| Cell | Labels | P1 - P2 | P2 - P3 | (P2 - P3) - (P1 - P2) |", "|---|---|---|---|---|"]
    for k, row in C.items():
        for lab in ["submitted", "corrected"]:
            if k.startswith("DREAMER") and lab == "submitted":
                continue
            cc = row[lab]["contrasts"]
            L.append(f"| {k} | {lab if k.startswith('DEAP') else 'unchanged'} | "
                     f"{cc['P1-P2']['diff']:+.3f} {ci_str(cc['P1-P2']['ci'])} | {cc['P2-P3']['diff']:+.3f} {ci_str(cc['P2-P3']['ci'])} | "
                     f"{cc['(P2-P3)-(P1-P2)']['diff']:+.3f} {ci_str(cc['(P2-P3)-(P1-P2)']['ci'])} |")
    L += ["", f"Subject-identity decoding (label-free): DEAP {res['DEAP_subject_id_acc']['corrected']:.3f}, "
          f"DREAMER {res['DREAMER_subject_id_acc']['corrected']:.3f}, unchanged by the correction.", ""]
    L += ["## Binary labels changed by the correction", "",
          "The .dat mirror reflects both ratings on 439 of 1,280 DEAP trials. Because the reflection only hits trials "
          "rated above about 5, it also moves the global median, so the binary labels change on more trials than were "
          "reflected.", "", "| DEAP cell | trials whose binary label changed |", "|---|---|"]
    for k, v in res["binary_label_flips"].items():
        if k.startswith("DEAP"):
            L.append(f"| {k} | {v['trials']} of {v['of']} |")
    L += ["", "## Affected manuscript statements", ""]
    for c in claims:
        L.append(f"- **{c['where']}**, \"{c['text']}\"")
        if isinstance(c["verdict"], dict):
            for k, v in c["verdict"].items():
                L.append(f"  - {k}: {v}")
        else:
            L.append(f"  - {c['verdict']}")
        if "corrected" in c and isinstance(c["corrected"], list):
            L.append(f"  - submitted {c['submitted'][0]:.3f} to {c['submitted'][1]:.3f}; corrected {c['corrected'][0]:.3f} to {c['corrected'][1]:.3f}")
        if c is claims[0]:
            L.append(f"  - corrected DEAP valence leak-free cells with intervals above 0.50: {', '.join(c['corrected_valence_cells_above_chance']) or 'none'}")
        if c is claims[1]:
            for t in ["valence", "arousal"]:
                L.append(f"  - {t}: submitted {c['submitted'][t][0]:.3f} to {c['submitted'][t][1]:.3f}; corrected {c['corrected'][t][0]:.3f} to {c['corrected'][t][1]:.3f}")
    L += ["", "Not computable here and to be rewritten by hand: TEX:109's statement that the companion study \"finds the "
          "same asymmetry independently\". This pipeline's surviving leak-free DEAP effect is now in valence, not arousal.", ""]
    (REV1 / "LABEL_CORRECTION.md").write_text("\n".join(L))
    print("\n".join(L))
