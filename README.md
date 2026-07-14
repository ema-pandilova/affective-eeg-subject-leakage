# Subject-identity leakage in affective EEG

Code and data for the Perspective:

> **Subject-identity leakage and the category error in EEG-based emotion recognition.**

Much of the affective-EEG literature reports **within-subject state markers** as if they were
**population-level biomarkers**. The dominant evaluation protocols hide the difference by letting
subject identity leak into the test set. This repository holds the two artefacts behind that
argument: a self-contained demonstration notebook, and the literature audit.

The full empirical study is a companion paper with its own repository:
**[qeeg-emotion-pipeline](https://github.com/ema-pandilova/qeeg-emotion-pipeline)**.

---

## 1. The demonstration (`notebook/`)

`demo_leakage_collapse.ipynb` runs one model and one feature set on DEAP and DREAMER under **four
evaluation protocols that differ only in how the data is split**:

| # | Protocol | Same trial across split? | Same participant? |
|---|---|---|---|
| 1 | Window-pooled *k*-fold | yes | yes |
| 2 | **Trial-grouped, participant-pooled** | **no** | yes |
| 3 | Subject-grouped windows | no | **no** |
| 4 | Leave-one-subject-out (trial-level) | no | no |

Because consecutive protocols differ in exactly one respect, the gap between adjacent rows isolates a
single leakage channel: **1→2 is correlated-window leakage, 2→3 is participant identity.** This is the
control the argument needs — a pooled-versus-subject-grouped comparison removes *both at once* and so
cannot attribute the loss to either.

What it finds:

- Which channel dominates is **dataset-dependent**: participant identity on DEAP (0.136 AUC),
  correlated windows on DREAMER (0.279).
- Every leak-free estimate sits at chance, while the same features decode **which participant**
  produced a recording at 99% (DEAP) and 88% (DREAMER), against chance of 3% and 4%.
- Participant overlap pays chiefly by exposing each participant's **label prior**: re-run with
  per-subject-median labels, which flatten per-subject base rates, and the advantage disappears.

Two methodological points the notebook is deliberate about:

- **Intervals resample subjects, not windows.** Resampling the tens of thousands of correlated windows
  treats them as independent observations and gives intervals several times too narrow — enough to
  make a chance-level cell look significantly *below* chance.
- **The label rule is stated, not assumed.** The primary labels use a single **global median**, which
  is *not* per-participant and leaves per-subject base rates spread from 0.28 to 1.00, so the
  label-prior channel is active. A per-subject-median run is included as a sensitivity analysis; note
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

## 3. Data (not included)

| Dataset | Get it from |
|---|---|
| DEAP | <https://www.eecs.qmul.ac.uk/mmv/datasets/deap/> (preprocessed Python, `s01.dat … s32.dat`) |
| DREAMER | <https://zenodo.org/record/546113> (`DREAMER.mat`) |

Both are third-party and obtained under their custodians' own terms.

## 4. Layout

```
notebook/
  demo_leakage_collapse.ipynb   executed, self-contained demonstration
  build_notebook.py             regenerates the notebook (edit here)
  run_notebook.py               executes it in-process (no Jupyter kernel needed)
  run_protocols.py              the four-protocol sweep, subject-level bootstrap
  eegnet_collapse.py            EEGNet on raw EEG, single run
  eegnet_seeds.py               EEGNet across N seeds -> mean +/- sd
audit/
  build_audit.py                regenerates the coding sheet
  build_audit_supplement.py     tallies + the complete supplementary table
  literature_audit.csv/.md      the coding sheet
results/                        computed outputs (JSON)
figures/make_concept_figure.py  the conceptual figure
```

The manuscript is kept in Overleaf and is not tracked here.
