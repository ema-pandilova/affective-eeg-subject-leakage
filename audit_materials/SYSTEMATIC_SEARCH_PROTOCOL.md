# Literature audit: systematic search and double-coding protocol

Frontiers in Neuroscience manuscript 1953177, revision. Protocol version 1.3, 16 September 2026
(version 1.0, 14 September 2026; see the change log). **The design is frozen.** Version 1.3 adds
section 4.1, four clarifications of the existing eligibility rules, and changes nothing else.
This protocol is fixed before any search is run or any study is coded. Changes after that point are
recorded in the change log at the end, with the date and the reason.

## 1. Question and unit

For peer-reviewed studies that report EEG-only emotion decoding on DEAP, DREAMER or a SEED-family
dataset, the audit records how the headline result was evaluated (participant, trial and stimulus
separation, scoring unit, normalization scope, use of test-participant data, model selection) and
whether the paper states a population-level claim. The unit of analysis is the study. The audit
describes a sample. It does not estimate a field-wide prevalence, in Part A or in Part B, and no
percentage it yields is reported as a rate for affective-EEG research. Section 9 states the single
conclusion the design supports.

## 2. Two parts

**Part A, re-coding of the 33 studies in the submitted audit.** Two independent human coders code
all 33 studies with the rubric. The way these 33 were assembled is disclosed as it was: a
purposive set of dataset-origin papers, widely cited method papers, and papers added because they
report subject-independent results. Part A yields agreement statistics and a corrected
illustrative table. It supports no prevalence statement.

**Part B, systematic search with a seeded random sample.** The authors chose option B on 16 September
2026, so Part B is being run. The searches below are run, logged and de-duplicated; records are
screened in a seeded random order until the target number of eligible studies is reached; the sample
is double-coded.

## 3. Searches (Part B)

Databases: Scopus and Web of Science Core Collection. Both are searched on the same day, and the
date, the string exactly as run, the limits and the number of records returned are entered in
`search_log_template.csv`. The exported record files are kept unchanged.

Scopus (Advanced search):

```
TITLE-ABS-KEY ( ( eeg OR electroencephalogra* )
  AND ( emotion* OR valence OR arousal OR affective )
  AND ( recogni* OR classif* OR decod* OR detect* OR predict* )
  AND ( deap OR dreamer OR "SEED dataset" OR "SEED database" OR "SJTU Emotion EEG Dataset"
        OR "SEED-IV" OR "SEED-V" OR "SEED-VII" ) )
AND PUBYEAR > 2011 AND PUBYEAR < 2026
AND ( LIMIT-TO ( DOCTYPE , "ar" ) OR LIMIT-TO ( DOCTYPE , "cp" ) )
AND ( LIMIT-TO ( LANGUAGE , "English" ) )
```

Web of Science Core Collection (Advanced search):

```
TS=( (EEG OR electroencephalogra*)
  AND (emotion* OR valence OR arousal OR affective)
  AND (recogni* OR classif* OR decod* OR detect* OR predict*)
  AND (DEAP OR DREAMER OR "SEED dataset" OR "SEED database" OR "SJTU Emotion EEG Dataset"
       OR "SEED-IV" OR "SEED-V" OR "SEED-VII") )
Refined by: Publication Years 2012-2025; Document Types: Article OR Proceeding Paper; Languages: English
```

Date range: 1 January 2012 (the year DEAP was published) to 31 December 2025.

De-duplication: by DOI, then by normalized title and first author for records without a DOI. When a
conference paper and a later journal version report the same experiment, the journal version is
kept and the conference paper is excluded as a duplicate at full text.

### As executed, 15 September 2026

The search was run against OpenAlex rather than Scopus and Web of Science, which need institutional
credentials. OpenAlex is open and callable without an account, so the identification step is
reproducible by anyone from `partB/run_search.py` alone. The same concept, dataset, year and
document-type criteria apply; the exact strings, date and counts are in `partB/search_log.csv`.

Each of the eight dataset terms is run twice, over title-and-abstract and over title alone, because
several heavily cited studies have no abstract indexed and would otherwise be unreachable. Document
types include conference papers, as section 4 admits proceedings papers. Preprints and records with
no language field are retrieved and then excluded by the coders at screening, so every exclusion is
counted in the PRISMA flow rather than hidden inside the query. The year floor is 2011 rather than
2012 because OpenAlex dates the DEAP origin paper to its 2011 online publication; coders apply the
2012 to 2025 rule to the publication year of record.

Result: 2,844 records retrieved, 642 duplicates removed, a screening frame of 2,202 records, placed
in the seeded random order of section 5 and saved as `partB/screening_order.csv` before any screening
began.

Scope of the frame. A dataset-name query reaches only studies that name the dataset in the title or
abstract. Studies that use one of these datasets without naming it there fall outside the frame
whatever filters are used. This bounds what the sample can describe, as section 9 states.

## 4. Eligibility

Inclusion, all required (rubric field `E1`, confirmed at full text by `X1`):

1. a peer-reviewed primary study, meaning a journal article or a peer-reviewed conference paper,
   that reports its own emotion-decoding experiment;
2. at least one result from EEG alone, not fused with other signals, on DEAP, DREAMER or a
   SEED-family dataset (SEED, SEED-IV, SEED-V, SEED-VII);
3. the full text can be obtained.

Exclusion reasons, recorded as the first that applies (field `E2`): review, survey or tutorial; no
emotion-decoding experiment; no EEG-only result on the named datasets; duplicate or earlier version
of an included study; not peer reviewed (preprint, thesis); full text not obtainable; other, with a
note. The dataset-origin papers for DEAP, DREAMER and SEED are eligible because they report their
own EEG-only classification.

### 4.1 Clarifications

Added 16 September 2026, after an AI-assisted workflow pilot and before any human screening or
coding. Each resolves a case the criteria above did not settle. They restate the existing rules for
recurring situations; they do not widen or narrow what is eligible.

**Book chapters.** Criterion 1 admits a journal article or a peer-reviewed conference paper. A book
chapter is eligible when the volume is conference proceedings published in book form, which several
Springer series are, and the paper reports its own experiment. Decide from the volume, not the
publisher: a volume presenting the papers of a named conference qualifies, and an edited collection,
a monograph or a handbook does not. A chapter that fails this test is excluded as `other`, with the
volume type in the note. Where the volume type cannot be determined, code `unsure`.

**A preprint whose published version appears later in the order.** Screening is sequential and no
coder looks ahead, so a preprint is judged on its own: exclude it as `not_peer_reviewed`, the first
applicable reason, and record the other version's position in the note if you happen to know it.
`duplicate` applies only against a study already included at an earlier position. Whether the
published version is later included changes nothing about the preprint's exclusion.

**Multimodal studies with no stated EEG-only result.** Criterion 2 requires at least one result from
EEG alone. The absence of an EEG-only number in the abstract is not sufficient to exclude, because
fusion papers routinely report an EEG-only ablation without mentioning it there. Check the full text.
If the full text contains no EEG-only result on a named dataset, exclude as `frame`. If the full text
cannot be checked, code `unsure` rather than guessing in either direction.

**What "the full text can be obtained" means.** It means obtainable by you, through institutional
access or interlibrary loan, not retrievable by an automated download. A publisher paywall your
library passes is not a reason to exclude. Reserve `no_full_text` for a paper you genuinely cannot
read after trying your library, and name what you tried in the note.

## 5. Screening and sampling (Part B)

1. De-duplicated records are placed in a random order with seed 20260914 (NumPy
   `default_rng(20260914).permutation`), and the ordered list is saved before screening starts.
2. Both coders screen titles and abstracts independently in that order, opening the full text
   whenever the abstract does not settle a criterion. Disagreements and `unsure` answers go to the
   adjudicator.
3. Screening continues in order until 45 studies are eligible after adjudication. The 45 form the
   coding sample; the position in the list at which the target was reached is recorded, so that the
   sample is a simple random sample of the eligible records screened.
4. Counts for every stage are entered in `prisma_flow_counts_template.csv` and reported as a PRISMA
   flow diagram in the Supplementary Material.

## 6. Coders and independence

- Two human coders, named before coding starts. Neither may be an AI system, and neither may be the
  person who produced the original coding of the 33 studies. Whether a coder is a co-author, and
  what each coder had read of the manuscript beforehand, is disclosed.
- A third person, the adjudicator, settles disagreements and does not code.
- No language model is used for screening or coding decisions. Tools may be used to retrieve full
  texts.
- Each coder works in a separate copy of `second_coder_sheet_blank.csv` (or the Audit Coding Bench),
  does not see the other coder's sheet, the submitted Supplementary Table S1 or the original coding,
  and signs off the sheet as final before agreement is computed.
- Calibration: before coding the sample, both coders code the same three frame papers that are not in
  the sample and discuss the rubric. Calibration answers are not counted.

## 7. Coding

The rubric is `CODING_RUBRIC.md` (machine-readable: `coding_rubric_v1.1.csv`). Every study is coded
from the version of record at the DOI. Answers to split, normalization and claim questions carry a
quote with page or section (`Q_split`, `Q_norm`, `Q_claim`). The eight primary fields are `E1`, `X1`,
`S2` (participants disjoint), `S3` (trials disjoint), `N1` (normalization scope), `T1` (use of
test-participant data), `R1` (any participant-disjoint result) and `C1` (population-level claim).

## 8. Agreement and adjudication

Agreement is computed with `compute_agreement.py` on the two final sheets before adjudication:

```
python compute_agreement.py coding_rubric_v1.1.csv coderA.csv coderB.csv --boot 2000 --seed 20260914 --out agreement.csv
```

For each categorical field it reports percent agreement, Cohen's kappa, Gwet's AC1 and PABAK, each
with a 95% percentile bootstrap interval resampling studies (2,000 draws), and a sensitivity analysis
without `unclear` answers. Two fields have a defensible category order, `C1` (no, generic, explicit)
and `S5` (not_reported, inferred, explicit), and a linearly weighted kappa is reported for those as
well, because a disagreement between adjacent categories is milder than one between the extremes.
Every other field is treated as nominal: its categories have no order, and several carry an `unclear`
or `na` level that sits outside any ordering, so weighting would impose a scale the rubric does not
define. Screening agreement on `E1` and `E2` is computed the same way with `--stage screen`. Numeric fields are compared within 0.005 after percentages are converted
to proportions. Questions are compared only for studies where both coders reached them. The script
refuses to run on two sheets from the same coder or on a sheet whose coder name looks like a
language model.

After agreement is computed, every disagreement is settled by the adjudicator from the quoted
evidence, and the adjudicated values are the ones reported in the audit tables. Agreement statistics
are always the pre-adjudication values.

## 9. Reporting

- Search strings, dates, limits and record counts; the PRISMA flow diagram (Part B).
- Agreement for every field, primary fields in the main text or a main-text table, all fields in the
  Supplementary Material.
- The adjudicated coding sheet as Supplementary Table S1, with quotes.
- Counts described as properties of the coded sample. Part A supports no prevalence statement.

### The conclusion this design supports

Part B supports one conclusion and the manuscript states no more than it:

> Evaluation and reporting practices in the systematically identified sample show that leakage-prone
> or insufficiently documented protocols remain present in the DEAP, DREAMER and SEED literature.

No prevalence figure for the field is reported, and none is implied. Two limits make that the correct
ceiling. The frame contains only studies that name a dataset in the title or abstract, so studies that
use one without naming it there are outside it. And the search was run against one database. Counts
are therefore described as properties of the coded sample, never as a rate for affective-EEG research.

**The audit design is frozen as of 16 September 2026.** Sections 1 to 9 are not revised further unless
a reviewer comment explicitly requires it.

## 10. Materials in this folder

| File | Purpose |
|---|---|
| `SYSTEMATIC_SEARCH_PROTOCOL.md` | This protocol |
| `CODING_RUBRIC.md`, `coding_rubric_v1.1.csv` | Rubric, readable and machine-readable |
| `second_coder_sheet_blank.csv` | Blank sheet for the 33 Part A studies; columns match `compute_agreement.py` |
| `search_log_template.csv` | Search log template for Part B |
| `partB/run_search.py` | Runs the Part B identification and de-duplication and writes the seeded screening order |
| `partB/search_log.csv` | The queries as actually run, with date and counts |
| `partB/records_raw.csv`, `partB/records_deduped.csv` | Retrieved records, before and after de-duplication |
| `partB/screening_order.csv` | The 2,202-record frame in seeded random order, screening columns blank |
| `partB/prisma_counts.csv` | PRISMA identification counts |
| `partB/CODER_INSTRUCTIONS.md` | What the two coders do, start to finish |
| `partB/coderA_screening.csv`, `partB/coderB_screening.csv` | One blank screening sheet per coder, identical rows in the frozen order |
| `partB/coderA_calibration.csv`, `partB/coderB_calibration.csv` | The three calibration records of section 6, taken from the tail of the order so they cannot collide with the sample |
| `partB/make_coder_pack.py` | Regenerates the sheets above from the frozen order |
| `partB/make_coding_sheets.py` | Turns the two finished screening sheets into the coding sheets, the bench work package and the PRISMA screening counts |
| `partB/adjudication_template.csv` | Where the adjudicator records each resolved screening disagreement |
| `prisma_flow_counts_template.csv` | Stage counts for the PRISMA diagram |
| `compute_agreement.py` | Agreement statistics with bootstrap intervals |
| `study_links.csv` | Resolved DOI, venue, peer-review status and an open full text where one exists, for the 33 Part A studies |
| `bench/` | The Audit Coding Bench: a self-contained offline page for coding, with the codebook and the 33 study records. Coder name fields ship blank. |

## Change log

| Date | Change | Reason |
|---|---|---|
| 14 September 2026 | Version 1.0 | |
| 15 September 2026 | Version 1.1. `study_links.csv` added. | Retrieval aid only. Every Part A study was resolved against Crossref and OpenAlex; 15 of the 33 have an open full text and 18 need library access. No coding field is pre-filled. |
| 15 September 2026 | Two Part A studies are arXiv preprints: `Kukhilava2025` and `Wang2024_ssl`. | Section 4 excludes preprints, but Part A re-codes the submitted 33 as they were assembled rather than a set filtered by this protocol. Both remain in Part A and are marked in `study_links.csv`; coders record them as not peer reviewed (`E2`) as the rubric directs. The exclusion rule applies without exception to the Part B sample. |
| 15 September 2026 | `Zhang2025_mdjpt` repointed from arXiv 2510.22197 to the version of record, NeurIPS 38 (2025), doi 10.52202/085713-5515. | A peer-reviewed version appeared after the sheet was built. Section 7 requires coding from the version of record. |
| 15 September 2026 | `Jiang2024_labram` DOI filled with arXiv 2405.18765. | The sheet carried no identifier. The version of record is the ICLR 2024 conference paper, which has no publisher DOI; the arXiv identifier is given for retrieval only and the paper is peer reviewed. |
| 16 September 2026 | Version 1.2. Audit option B selected; Part B identification run and the screening order fixed. | The authors chose the systematic version because it is what Reviewer 1 asked for. |
| 16 September 2026 | Part B searched OpenAlex instead of Scopus and Web of Science. | Those two need institutional credentials. OpenAlex is open, so the whole identification step is reproducible from the released script without an account. The concept, dataset, year and document-type criteria are unchanged. |
| 16 September 2026 | Each dataset term is searched over title-and-abstract and over title alone; conference papers included; preprints and records without a language field retrieved and excluded at screening; year floor 2011. | A first run excluded conference papers, which section 4 admits, dropped records whose language field is empty, and used a 2012 floor that excluded the DEAP origin paper because OpenAlex dates it to its 2011 online publication. Retrieving wider and excluding at screening puts every exclusion in the PRISMA flow instead of hiding it in the query. |
| 16 September 2026 | Section 9 states the single conclusion the design supports and rules out any prevalence claim. Design frozen. | Keeps the audit to what Reviewer 1 requested: a reproducible search, two coders, agreement, cautious conclusions. FACED is not audited; it is an external replication dataset in the experiments and needs no literature component. |
| 16 September 2026 | Version 1.3. Section 4.1 added: four clarifications of the eligibility rules, covering peer-reviewed book chapters, a preprint whose published version appears later in the ordered frame, multimodal studies that report no EEG-only result, and what counts as an obtainable full text. | An AI-assisted workflow pilot screened a stretch of the frame to test the materials and exercise the tooling. It showed that the recurring ambiguities fell on exactly these four cases, and that disagreement concentrated there rather than being spread across the criteria. Writing the rules down before human coding begins prevents two coders resolving the same ambiguity differently and depressing the reliability estimate for a reason that has nothing to do with the literature. The clarifications restate the existing criteria for recurring situations; they do not widen or narrow eligibility. |
| 16 September 2026 | The pilot contributes no observation to the audit. Its outputs are archived outside the audit materials under names that cannot be mistaken for coder sheets. | The pilot was produced by an AI model, not by a human coder. Protocol section 6 requires two human coders and forbids a language model from making screening or coding decisions. No pilot row enters the audit dataset, the screening decisions, the coding decisions or the agreement statistics, which are computed only from the two human coders' own sheets before adjudication. |
| 16 September 2026 | Coders must have institutional full-text access. | Coding requires a verbatim quotation with a page or section number for the split, normalization and claim questions, which cannot be taken from an abstract. The pilot could not retrieve 40 of 45 full texts from IEEE, Elsevier, Springer and SSRN without a library. |
