# Subject-identity leakage in affective EEG

Code and data for the Perspective:

> **Subject Identity, Evaluation Leakage, and the Category Error in EEG-Based Emotion Recognition.**

Much of the affective-EEG literature reports **within-subject state markers** as if they were
**population-level biomarkers**. The dominant evaluation protocols hide the difference by letting
subject identity leak into the test set. This repository holds the two artefacts behind that
argument: a self-contained demonstration notebook, and the literature audit.

The full empirical study is a companion paper with its own repository:
**[qeeg-emotion-pipeline](https://github.com/ema-pandilova/qeeg-emotion-pipeline)**.

> ### ⚠ DEAP ratings: check your copy before you trust any DEAP number
>
> The copy of the DEAP preprocessed release used for the submitted version of this paper — a
> redistributed copy of the official files — carried valence **and** arousal reflected on the rating
> scale (`9 − x`) on **439 of the 1,280 trials**, across all 32 participants. The EEG signals and the
> dominance and liking ratings in that copy are intact. Because the reflection only moves ratings
> above the scale midpoint, it also shifts the median, so the binary labels differ on **733 trials for
> valence and 696 for arousal**.
>
> Every DEAP number in the published revision uses the official ratings from
> `participant_ratings.xls`. `notebook/deap_labels.py` performs and verifies the join, and
> `notebook/rev1_labelfix.sh` reproduces the submitted numbers from the corrupted labels first, as a
> gate, before recomputing with the corrected ones. **Run it against your own copy before reporting
> any DEAP result.** If you downloaded DEAP from its custodians rather than a mirror, your labels are
> most likely already correct.

---

## 1. The demonstration (`notebook/`)

`demo_leakage_collapse.ipynb` runs one model and one feature set on DEAP and DREAMER under **four
evaluation protocols**:

| # | Protocol | Same trial across split? | Same participant? |
|---|---|---|---|
| 1 | Window-pooled *k*-fold | yes | yes |
| 2 | **Trial-grouped, participant-pooled** | **no** | yes |
| 3 | Subject-grouped windows | no | **no** |
| 4 | Leave-one-subject-out (trial-level) | no | no |

Protocols 1 to 3 are identical except for the grouping variable, so the gap between adjacent rows isolates a
single leakage channel: **1→2 is correlated-window leakage, 2→3 is participant identity.** This is the
control the argument needs — a pooled-versus-subject-grouped comparison removes *both at once* and so
cannot attribute the loss to either. Protocol 4 also switches to leave-one-subject-out and fits a train-fold
scaler, so it is a robustness check on the leak-free estimate rather than an isolated channel.

What it finds (trial-level AUC, training-median labels, corrected DEAP ratings):

- Which channel dominates is **dataset- and target-dependent**. Splitting the drop into its two
  channels (correlated windows, then participant overlap) gives +0.077 and +0.091 for DEAP valence,
  +0.070 and +0.190 for DEAP arousal, +0.279 and +0.002 for DREAMER valence, and +0.248 and +0.133
  for DREAMER arousal. On DREAMER the correlated-window channel dominates; on DEAP participant
  identity is the larger channel for arousal and roughly matches it for valence.
- Performance on unseen participants is **modest**: protocols 3 and 4 give AUCs from 0.454 to 0.565.
  Meanwhile the same features decode **which participant** produced a recording at 99% (DEAP) and
  88% (DREAMER), against chance of 3% and 4%.
- Participant overlap pays largely by exposing each participant's **label prior**. Re-run with
  per-subject-median labels, which flatten per-subject base rates to near 0.50, and the
  participant-overlap advantage falls to +0.031 (DEAP valence), +0.007 (DEAP arousal), −0.028
  (DREAMER valence) and +0.049 (DREAMER arousal) — it essentially disappears in all four cells.
  The paper tests this mechanism more carefully, with a no-EEG participant-prior baseline, a
  within/between decomposition and class-balanced reweighting, and finds that the label-prior
  account holds for arousal but does not explain the DEAP valence advantage.

Two methodological points the notebook is deliberate about:

- **Intervals resample subjects, not windows.** Resampling the tens of thousands of correlated windows
  treats them as independent observations and gives intervals several times too narrow — enough to
  make a chance-level cell look significantly *below* chance.
- **The label rule is stated, not assumed.** The primary labels use a single **global median**, which
  is *not* per-participant and leaves per-subject base rates spread across 0.35 to 0.75 for DEAP
  valence, 0.17 to 0.80 for DEAP arousal, 0.39 to 0.78 for DREAMER valence and 0.50 to 0.94 for
  DREAMER arousal, so the label-prior channel is active. A per-subject-median run is included as a sensitivity analysis; note
  that it needs the held-out participant's own ratings, so it is a diagnostic, not a deployable
  protocol.

```bash
python -m venv venv && ./venv/bin/pip install -r requirements.txt
export QEEG_DATA_ROOT=/path/to/data-root      # folder holding data/deap/... and DREAMER.mat

./venv/bin/python notebook/run_protocols.py                  # four-protocol sweep -> results/protocols.json
./venv/bin/python notebook/run_notebook.py                   # execute the notebook end-to-end
./venv/bin/python notebook/eegnet_seeds.py DREAMER 5 cuda:0  # deep-model check, multi-seed
```

`eegnet_collapse.py` / `eegnet_seeds.py` repeat the collapse with an EEGNet trained end-to-end on the
**raw full montage** (all 32 DEAP / 14 DREAMER electrodes), so the effect is not an artefact of the
handcrafted features or of the compact frontal montage.

Edit `build_notebook.py`, not the `.ipynb` — the notebook is a build artefact.

## 2. The literature audit (`audit/`)

`literature_audit.csv` / `.md` code 33 affective-EEG studies on DEAP, SEED and DREAMER. Regenerate
with `python audit/build_audit.py`.

Two axes are graded **separately**, which matters:

- **Leakage risk** grades the *split* only — whether participants bridge the train/test boundary.
- **Normalization scope** is graded on its own axis, because a subject-independent split can still be
  compromised by statistics estimated from the held-out participant's own recording. Per-subject
  normalization is therefore **not** treated as automatically clean.

Of the 12 studies with a clean subject-independent split, only 8 report verified train-only
normalization; the other 4 could not be confirmed from their text.

**This is a purposive, single-coder sample.** It shows that leaky evaluation is common in influential
work. It is *not* a random sample, cannot support a prevalence estimate for the field, and none is
offered.

## 3. The revision analyses (`notebook/rev1_*.py`)

Written for the Frontiers major revision. These reproduce every number, table and figure in the
revised manuscript, on corrected DEAP labels and with a third dataset, FACED (123 participants).

| Script | What it produces |
|---|---|
| `rev1_common.py` | Shared data loading, label schemes, fold construction, trial aggregation, participant bootstrap |
| `rev1_labelfix.sh` | The label correction end to end: verify, reproduce the submission as a gate, recompute, write `PROVENANCE.json` |
| `rev1_e0_descriptives.py` | Dataset descriptives and identity decodability |
| `rev1_e1_protocols.py` | The protocol ladder P1/P2/P2B/P3/P4 with no-EEG baselines |
| `rev1_e3_identity_removal.py` | Whitening and removal of between-participant directions |
| `rev1_e3b_exploitation.py` | Within/between decomposition and label-prior reweighting |
| `rev1_e4_normalization.py` | The 2×2 normalization ablation (grouping × scope) |
| `rev1_e5_stimulus.py` | Size-matched participant-block × stimulus-block design |
| `rev1_tables_figures.py` | Every manuscript table and figure from the result JSONs |
| `faced_build.py` | Builds the FACED cache from the authors' processed release |

Protocols: **P1** window-pooled *k*-fold, **P2** trial-grouped, **P2B** FACED presentation-block
grouped, **P3** participant-grouped, **P4** leave-one-participant-out. Labels are thresholded at the
**median of the training rows of each fold**, so no held-out rating enters the label definition.
Intervals are percentile participant bootstraps (1,000 draws, one shared draw matrix per dataset, so
contrasts are paired). The classifier is fixed throughout: XGBoost, 200 trees, depth 3, lr 0.1,
subsample and colsample 0.8, seed 17, untuned.

Summary results are in `results/rev1/`. Out-of-fold predictions, bootstrap draw matrices, run logs
and generated figures are deliberately not tracked; they regenerate from these scripts and the
recorded seed. `results/rev1/PROVENANCE.json` ties each definitive output to the Git commit it ran
from, and `rev1_labelfix.sh` refuses to run when a pipeline file differs from `HEAD`.

## 4. The systematic-audit materials (`audit_materials/`)

Materials for the two-coder audit, released so the procedure is inspectable before it is run:
the search protocol with exact strings and eligibility rules, the coding rubric in readable and
machine-readable form, a blank 33-study coding sheet, a resolved full-text index (`study_links.csv`),
and `compute_agreement.py`, which computes Cohen's kappa, Gwet's AC1 and PABAK with bootstrap
intervals and refuses two sheets from the same coder or a coder name that looks like a language model.

**The audit reported in the paper remains a single-coder purposive sample and is described as one.**
Agreement statistics cannot be reported until two people have independently coded.

## 5. Data (not included)

| Dataset | Get it from |
|---|---|
| DEAP | <https://www.eecs.qmul.ac.uk/mmv/datasets/deap/> (preprocessed Python, `s01.dat … s32.dat`, plus `metadata/participant_ratings.xls`, which the label check needs) |
| DREAMER | <https://zenodo.org/record/546113> (`DREAMER.mat`) |
| FACED | Synapse `syn50614194` (the authors' processed release); per-clip ratings via the NEMAR BIDS conversion `nm000112` |

All three are third-party and obtained under their custodians' own terms. Get DEAP from its
custodians rather than a mirror; see the ratings warning above.

## 6. Layout

```
notebook/
  demo_leakage_collapse.ipynb   executed, self-contained demonstration
  build_notebook.py             regenerates the notebook (edit here)
  run_notebook.py               executes it in-process (no Jupyter kernel needed)
  run_protocols.py              the four-protocol sweep, subject-level bootstrap
  eegnet_collapse.py            EEGNet on raw EEG, single run
  eegnet_seeds.py               EEGNet across N seeds -> mean +/- sd
  deap_labels.py                DEAP rating join + verification against the official file
  rev1_labelfix.sh              label correction end to end, with the reproduction gate
  rev1_common.py                shared definitions for the revision analyses
  rev1_e0/e1/e3/e3b/e4/e5*.py   the revision analyses (see section 3)
  rev1_tables_figures.py        manuscript tables and figures
  faced_build.py                builds the FACED cache
audit/
  build_audit.py                regenerates the coding sheet
  build_audit_supplement.py     tallies + the complete supplementary table
  literature_audit.csv/.md      the coding sheet
audit_materials/                two-coder audit protocol, rubric, sheets, agreement script
results/                        computed outputs (JSON)
results/rev1/                   revision outputs + PROVENANCE.json
figures/make_protocol_figure.py the four-protocol decomposition figure
```

The manuscript is kept in Overleaf and is not tracked here.
