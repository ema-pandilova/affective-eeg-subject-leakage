# Literature audit: systematic search and double-coding protocol

Frontiers in Neuroscience manuscript 1953177, revision. Protocol version 1.1, 15 September 2026
(version 1.0, 14 September 2026; see the change log).
This protocol is fixed before any search is run or any study is coded. Changes after that point are
recorded in the change log at the end, with the date and the reason.

## 1. Question and unit

For peer-reviewed studies that report EEG-only emotion decoding on DEAP, DREAMER or a SEED-family
dataset, the audit records how the headline result was evaluated (participant, trial and stimulus
separation, scoring unit, normalization scope, use of test-participant data, model selection) and
whether the paper states a population-level claim. The unit of analysis is the study. The audit
describes a sample; it does not estimate a field-wide prevalence unless the sample in Part B is
drawn as specified here, and even then any rate is reported as an estimate for the searched
databases, date range and eligibility rules only.

## 2. Two parts

**Part A, re-coding of the 33 studies in the submitted audit.** Two independent human coders code
all 33 studies with the rubric. The way these 33 were assembled is disclosed as it was: a
purposive set of dataset-origin papers, widely cited method papers, and papers added because they
report subject-independent results. Part A yields agreement statistics and a corrected
illustrative table. It supports no prevalence statement.

**Part B, systematic search with a seeded random sample.** Run only if the authors choose audit
option B. The searches below are run, logged and de-duplicated; records are screened in a seeded
random order until the target number of eligible studies is reached; the sample is double-coded.

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
without `unclear` answers. Numeric fields are compared within 0.005 after percentages are converted
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
- Counts described as properties of the coded sample. Part A supports no prevalence statement. Part B
  counts are reported as estimates for eligible studies indexed in the two databases over 2012 to 2025.

## 10. Materials in this folder

| File | Purpose |
|---|---|
| `SYSTEMATIC_SEARCH_PROTOCOL.md` | This protocol |
| `CODING_RUBRIC.md`, `coding_rubric_v1.1.csv` | Rubric, readable and machine-readable |
| `second_coder_sheet_blank.csv` | Blank sheet for the 33 Part A studies; columns match `compute_agreement.py` |
| `search_log_template.csv` | Search log for Part B |
| `prisma_flow_counts_template.csv` | Stage counts for the PRISMA diagram |
| `compute_agreement.py` | Agreement statistics with bootstrap intervals |
| `study_links.csv` | Resolved DOI, venue, peer-review status and an open full text where one exists, for the 33 Part A studies |

## Change log

| Date | Change | Reason |
|---|---|---|
| 14 September 2026 | Version 1.0 | |
| 15 September 2026 | Version 1.1. `study_links.csv` added. | Retrieval aid only. Every Part A study was resolved against Crossref and OpenAlex; 15 of the 33 have an open full text and 18 need library access. No coding field is pre-filled. |
| 15 September 2026 | Two Part A studies are arXiv preprints: `Kukhilava2025` and `Wang2024_ssl`. | Section 4 excludes preprints, but Part A re-codes the submitted 33 as they were assembled rather than a set filtered by this protocol. Both remain in Part A and are marked in `study_links.csv`; coders record them as not peer reviewed (`E2`) as the rubric directs. The exclusion rule applies without exception to the Part B sample. |
| 15 September 2026 | `Zhang2025_mdjpt` repointed from arXiv 2510.22197 to the version of record, NeurIPS 38 (2025), doi 10.52202/085713-5515. | A peer-reviewed version appeared after the sheet was built. Section 7 requires coding from the version of record. |
| 15 September 2026 | `Jiang2024_labram` DOI filled with arXiv 2405.18765. | The sheet carried no identifier. The version of record is the ICLR 2024 conference paper, which has no publisher DOI; the arXiv identifier is given for retrieval only and the paper is peer reviewed. |
