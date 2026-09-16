# Instructions for the two coders

Literature audit, Part B. Frontiers in Neuroscience manuscript 1953177.

You are one of two people independently screening and coding a sample of the affective-EEG
literature. The point of doing it twice is to measure how reliably the rubric can be applied, so the
value of your work depends entirely on the two of you working separately. Everything below exists to
protect that.

Read this page once before you start. It should take about ten minutes.

> **You need institutional library access.** The coding stage asks you to quote a sentence from each
> paper with its page or section number, so you need the full texts, and most of them sit behind
> IEEE, Elsevier or Springer paywalls. If you cannot reach those through your library, say so now
> rather than after screening.

---

## The five rules

1. **Do not look at the other coder's sheet**, at any stage, until both of you have signed off.
2. **Do not look at the audit in the submitted manuscript** (Supplementary Table S1), or at any
   earlier coding of these studies. If you have already read the manuscript, say so when you record
   your name; it is disclosed, not disqualifying.
3. **Do not use a language model to make any screening or coding decision.** You may use any tool to
   find and retrieve a paper. The judgement must be yours. The agreement script refuses sheets whose
   coder name looks like an AI system.
4. **Code from the version of record**, the published paper at its DOI, not from a preprint,
   a summary or an abstract, unless the record itself is a preprint.
5. **When a paper is genuinely ambiguous, record it as ambiguous.** Choose `unsure` at screening or
   `unclear` when coding. Do not guess to be helpful. Ambiguity is a finding about reporting, and an
   adjudicator resolves it afterwards.

---

## What you have

| File | What it is |
|---|---|
| `coderA_screening.csv` / `coderB_screening.csv` | Your screening sheet. 2,199 records in a fixed order. Take the one matching your letter. |
| `coderA_calibration.csv` / `coderB_calibration.csv` | Three practice records. Not part of the sample. |
| `../CODING_RUBRIC.md` | The rubric. Every question, with its decision rule. **This is the document you will actually use.** |
| `../coding_rubric_v1.1.csv` | The same rubric, machine-readable. |
| `../bench/audit-coding-bench.html` | Optional, for the coding stage. A page that walks you through the questions one at a time. Open it in a browser; it needs no internet and installs nothing. Load `bench-work-package-partB.json`, which the coordinator generates after screening. Do not load the file that ships in `bench/`: that one holds a different, earlier set of studies. |
| `../SYSTEMATIC_SEARCH_PROTOCOL.md` | The full protocol, if you want the background. You do not need to read it to do the work. |

The order of the records is fixed and randomised. Do not re-sort it. Work top to bottom.

---

## Step 1. Calibration, about an hour

Both of you code the three records in your calibration file, using the rubric. Then compare answers
and talk through every difference until you agree on what the rubric means.

These three answers are practice. They are not counted, not reported, and not part of the sample.
This is the one and only stage where you compare notes.

---

## Step 2. Screening, about half a day

Work down your screening sheet in order. For each record, decide from the title and abstract whether
the study belongs in the audit. Open the full text whenever the abstract does not settle it.

Fill in four columns:

- `coder_name` — your name, spelled the same way on every row
- `date_screened` — the date, as `2026-09-20`
- `E1` — `eligible`, `not_eligible`, or `unsure`
- `E2` — only when `E1` is `not_eligible`: the first reason that applies, from the rubric
- `note` — optional, anything the adjudicator should know

A study is eligible when all three hold. It is a peer-reviewed primary study, meaning a journal
article or a peer-reviewed conference paper, reporting its own emotion-decoding experiment. It
reports at least one result from EEG alone, not fused with other signals, on DEAP, DREAMER, or a
SEED-family dataset (SEED, SEED-IV, SEED-V, SEED-VII). And the full text can be obtained. The
dataset-origin papers for DEAP, DREAMER and SEED are eligible.

When it is not eligible, `E2` records the **first** reason that applies, in this order:

| `E2` | Reason |
|---|---|
| `review` | Review, survey or tutorial |
| `no_decoding` | No emotion-decoding experiment |
| `frame` | No EEG-only result on DEAP, DREAMER or a SEED-family dataset |
| `duplicate` | Duplicate or earlier version of a study already included |
| `not_peer_reviewed` | Not peer reviewed: preprint, thesis |
| `no_full_text` | Full text not obtainable |
| `other` | Anything else, explained in the note |

The search deliberately retrieved more than is eligible, including preprints and records with no
language recorded, so that every exclusion is counted here rather than hidden inside a database
query. Excluding those records is expected and is part of the job.

**You will not screen all 2,199 records.** Screening stops once 45 eligible studies have been found.
A trial pass over the top of the list suggests that lands early, so **screen the first 100 and stop
there**. That should be an afternoon rather than a day. The coordinator will ask for more only if the
two of you together fall short of 45 once disagreements are settled.

### Four cases that come up repeatedly

These are the situations the criteria above do not settle on their own. They are section 4.1 of the
protocol, written down before anyone started so that the two of you resolve them the same way.

**A book chapter** is eligible when the volume is conference proceedings published in book form,
which several Springer series are, and the paper reports its own experiment. Judge the volume, not
the publisher: a volume presenting the papers of a named conference qualifies, an edited collection
or a handbook does not. A chapter that fails the test is `not_eligible` with reason `other`, noting
the volume type. If you cannot tell what the volume is, `unsure`. There are a lot of these.

**A preprint whose published version appears further down the list.** Judge the preprint on its own
and exclude it as `not_peer_reviewed`. Do not look ahead in the list. `duplicate` is only for a study
already included at an earlier position.

**A multimodal study that reports no EEG-only result.** The criterion needs at least one EEG-alone
result. An abstract that mentions only fused results is not enough to exclude, because these papers
often report an EEG-only ablation without saying so in the abstract. Check the full text. If there is
genuinely no EEG-only result on one of the named datasets, exclude as `frame`. If you cannot check
the full text, `unsure`.

**"The full text can be obtained"** means you can get it, through your library or interlibrary loan.
A paywall your library passes is not a reason to exclude. Use `no_full_text` only for a paper you
genuinely cannot read after trying, and say what you tried in the note.

Save your sheet under your own name, for example `coderA_screening_2026-09-20.csv`.

---

## Step 3. Adjudication, not your job

The coordinator runs a script that compares the two sheets, lists every disagreement and every
`unsure`, and passes them to a third person. That person settles them and does not code. You may be
asked what you meant by a note; you will not be asked to change an answer to match.

This step fixes which 45 studies are coded, and produces `coderA_coding.csv` and `coderB_coding.csv`.

---

## Step 4. Coding, roughly one working day

Now you code the 45 studies properly, from their full texts, using the rubric. Take your coding sheet
and fill in one row per study.

The eight questions that matter most are `E1`, `X1`, `S2` (were participants disjoint between
training and test), `S3` (were trials disjoint), `N1` (what was normalisation computed over), `T1`
(was any test-participant data used), `R1` (is any participant-disjoint result reported at all), and
`C1` (does the paper make a population-level claim). Agreement on these is what gets reported.

Three columns ask for a **quote**: `Q_split`, `Q_norm`, `Q_claim`. Paste the sentence from the paper
that your answer rests on, with a section or page number. This matters more than it looks. It is what
lets the adjudicator resolve a disagreement without re-reading the whole paper, and it is what a
reader of the published audit can check.

`minutes` is optional. If you fill it in, we can report how long coding actually takes, which almost
no audit does.

When every row is done, save the sheet and tell the coordinator it is final. Do not revise it
afterwards: agreement is computed on the sheets as they stood before adjudication, so a later edit
would quietly inflate it.

---

## What happens to your work

Agreement is computed per question, before any adjudication: percent agreement, Cohen's kappa, and
weighted kappa where a question is ordinal, each with a confidence interval. Those numbers go into the
paper, along with a sensitivity analysis that sets aside the rows either of you marked `unclear`.

Then the adjudicator settles the disagreements, and the adjudicated values become the audit table.

You will be named in the paper as a coder, with a note saying whether you are a co-author and what
you had read of the manuscript beforehand. Tell the coordinator if you would rather not be named.

---

## If something is wrong

Tell the coordinator rather than working around it. If the rubric is silent on a case that keeps
recurring, that is worth knowing, and a rule added mid-way is recorded in the protocol's change log
with the date and the reason. What must not happen is two coders quietly resolving the same ambiguity
in two different ways.

---

## For the coordinator

After both screening sheets are final:

```bash
cd audit_materials/partB

# lists every disagreement and unsure in one pass
python3 make_coding_sheets.py coderA_screening_<date>.csv coderB_screening_<date>.csv

# after the adjudicator fills in adjudication.csv (copy adjudication_template.csv)
python3 make_coding_sheets.py coderA_screening_<date>.csv coderB_screening_<date>.csv \
        --adjudication adjudication.csv

# screening agreement
python3 ../compute_agreement.py ../coding_rubric_v1.1.csv \
        coderA_screening_<date>.csv coderB_screening_<date>.csv --stage screen
```

After both coding sheets are final:

```bash
python3 ../compute_agreement.py ../coding_rubric_v1.1.csv \
        coderA_coding_<date>.csv coderB_coding_<date>.csv --out agreement.csv
```

`make_coding_sheets.py` also writes `prisma_screening_counts.csv`, which holds the screened, excluded
and included counts and the position in the order at which the target was reached. Those are the
numbers the PRISMA diagram needs.
