# Audit coding rubric (codebook v1.1)

One row of `second_coder_sheet_blank.csv` per study. Fill the columns named by the field codes below. Answer a question only when its
"shown when" condition holds for your own earlier answers; otherwise leave it blank. Enter categorical answers as the code before
the "=" sign (for example `yes`, `pooled`, `train_only`). Give a quote with page or section for every split, normalization and claim
answer. Code the version of record at the DOI and write the version you used in `version_coded`.

Primary fields, used for the agreement statistics reported in the manuscript, are marked **primary**.


## Screen stage, Eligibility

Start from the title and abstract. Open the full text whenever the abstract does not settle one of the criteria.

### `E1` (primary)
Is this study eligible for the audit sample?
Decision rule: Eligible only if all three hold: (1) a peer-reviewed primary study, meaning a journal article or a peer-reviewed conference paper, reporting its own emotion-decoding experiment; (2) at least one result from EEG alone, not EEG fused with other signals, on DEAP, DREAMER or a SEED-family dataset, which is the same test the full-text check X1 applies; (3) the full text can be obtained. Choose Unsure when you cannot decide; the adjudicator settles it.
Options:
- `eligible`: Eligible
- `not_eligible`: Not eligible
- `unsure`: Unsure

### `E2`
Main reason it is not eligible
Shown when: `E1=not_eligible`
Decision rule: Pick the first reason that applies, in this order.
Options:
- `review`: Review, survey or tutorial
- `no_decoding`: No emotion-decoding experiment
- `frame`: No EEG-only result on DEAP, DREAMER or a SEED-family dataset
- `duplicate`: Duplicate or earlier version of an included study
- `not_peer_reviewed`: Not peer reviewed (preprint, thesis)
- `no_full_text`: Full text not obtainable
- `other`: Other, explained in the note

### `E_note`
Note
Decision rule: Anything the adjudicator should know.


## Code stage, Full-text check

### `X1` (primary)
On the full text, is this a primary emotion-decoding study with an EEG-only result on DEAP, DREAMER or a SEED-family dataset?
Decision rule: Code the version of record at the DOI. If you can only obtain another version, a preprint or an accepted manuscript, code that one and say so in the note. No for reviews, for studies of other tasks or datasets, and for studies whose only results fuse EEG with other signals. The dataset-origin papers for DEAP, DREAMER and SEED report their own EEG-only classification and are Yes. When No, say why in the note; the remaining questions are skipped.
Options:
- `yes`: Yes
- `no`: No


## Code stage, Headline result

The headline result is the first performance value (accuracy, F1, AUC or similar, not an improvement over a baseline) stated in the abstract for an EEG-only emotion-decoding result on DEAP, DREAMER or a SEED-family dataset. Skip earlier values that fuse modalities or come from other datasets. If the abstract gives no such value, use the first main results table that reports one, and take the EEG-only row of the proposed method, or the best EEG-only row when the paper proposes no method, as in dataset and benchmark papers. Whenever valence and arousal are reported together, code valence.

### `H1`
Dataset of the headline result
Shown when: `X1=yes`
Options:
- `DEAP`: DEAP
- `DREAMER`: DREAMER
- `SEED`: SEED
- `SEED-IV`: SEED-IV
- `SEED-V`: SEED-V
- `SEED-VII`: SEED-VII

### `H2`
Task of the headline result
Shown when: `X1=yes`
Options:
- `valence_binary`: Valence, two classes
- `arousal_binary`: Arousal, two classes
- `quadrant`: Valence-arousal quadrants, four classes
- `discrete`: Discrete emotion categories (for example SEED three classes)
- `other`: Other

### `H3`
Metric of the headline result
Shown when: `X1=yes`
Options:
- `accuracy`: Accuracy
- `f1`: F1
- `auc`: AUC
- `other`: Other

### `H4`
Headline value
Shown when: `X1=yes`
Decision rule: As printed, in the metric of H3. A percentage such as 94.5 is fine; it is converted to 0.945 for comparison. If a range or several folds are given, enter the highest value.


## Code stage, How the headline result was evaluated

### `S1`
Evaluation design
Shown when: `X1=yes`
Decision rule: Code the labeled data that trained the model before any adaptation or calibration, which T1 records separately. If the test participants were in that training data: one model per participant is Subject-dependent when the test data come from sessions also used in training, and Cross-session when the test session was not used; one model shared by several participants is Pooled, whatever the sessions. If the test participants were not in it: Participant-independent when some labeled training data came from the same dataset, including leave-one-subject-out across sessions, and Cross-dataset when none did.
Options:
- `subject_dependent`: Subject-dependent: a separate model for each participant, tested on sessions used in training
- `pooled`: Pooled: one model, participants mixed across training and test
- `independent`: Participant-independent within the dataset (leave-one-subject-out or participants grouped)
- `cross_dataset`: Cross-dataset: trained on one dataset, tested on another
- `cross_session`: Cross-session: a separate model for each participant, tested on a session not used in training
- `unclear`: Unclear

### `S2` (primary)
Were participants disjoint between training and test?
Shown when: `X1=yes`
Decision rule: Yes only if no labeled data from any test participant, meaning no window, trial or session, was used to train the model. Judge the split alone: unlabeled test-participant data belongs in T1, calibration or fine-tuning on the test participant belongs in T1, and tuning on test results belongs in M1. Subject-dependent, pooled and cross-session designs are No.
Options:
- `yes`: Yes
- `no`: No
- `unclear`: Unclear

### `S3` (primary)
Were trials disjoint between training and test?
Shown when: `X1=yes`
Decision rule: Yes only if no window cut from a test trial, meaning one viewing of one clip, appears in training. Random k-fold or a random split made after cutting trials into windows is No. A participant-disjoint split counts as Yes.
Options:
- `yes`: Yes
- `no`: No
- `unclear`: Unclear

### `S4`
Were stimuli disjoint between training and test?
Shown when: `X1=yes`
Decision rule: Yes only if no clip shown in the test set was used in training by any participant. Standard leave-one-subject-out on DEAP, DREAMER or SEED is No, because every participant watched the same clips.
Options:
- `yes`: Yes
- `no`: No
- `unclear`: Unclear

### `U1`
Unit on which the headline metric is computed
Shown when: `X1=yes`
Decision rule: Window when each window or segment prediction is scored as a separate test case, even if accuracies are averaged per participant afterwards. Trial when there is one prediction per trial, either from trial-level features or from window predictions aggregated to the trial. Participant when there is one prediction per participant. Code this regardless of the evaluation design.
Options:
- `window`: Window or segment
- `trial`: Trial
- `participant`: Participant
- `other`: Other, explained in the note
- `unclear`: Unclear

### `S5`
How clearly is the split reported?
Shown when: `X1=yes`
Decision rule: Stated explicitly: the paper says in words which unit was held out, whether windows, trials, sessions or participants. Inferred: you worked the unit out from other details, for example that the number of folds equals the number of participants, or that a 10-fold split of all samples never mentions trials or participants. Not reported: it cannot be worked out, in which case S2 or S3 is normally Unclear.
Options:
- `explicit`: Stated explicitly
- `inferred`: Inferred from the description
- `not_reported`: Not reported


## Code stage, Preprocessing and model selection

### `N1` (primary)
Scope of normalization or standardization for the headline result
Shown when: `X1=yes`
Decision rule: When several steps are described, for example baseline subtraction and then z-scoring, code the widest scope among them, in this order: over the whole dataset, per participant or recording, unclear, fit on training data, per window or trial. Per participant, session or recording means statistics computed over all of that data, including trials that end up in the test set. Statistics taken from a calibration slice of a test participant that is kept apart from the scored trials count as fit on training data. None described only when no normalization step is mentioned at all.
Options:
- `none`: None described
- `instance`: Per window or per trial only (for example baseline subtraction within a trial)
- `train_only`: Fit on training data only
- `participant_all`: Per participant, session or recording, over all of that data
- `dataset_all`: Over the whole dataset before the split
- `unclear`: Mentioned, but the scope cannot be determined

### `T1` (primary)
Was data from test participants used during training or adaptation?
Shown when: `X1=yes`
Decision rule: Not applicable when S1 is Subject-dependent, Pooled or Cross-session. For every other design, code what the model saw of the test participants during training or adaptation. If both unlabeled and labeled test-participant data were used, choose Labeled.
Options:
- `none`: No
- `unlabeled`: Unlabeled test-participant data (domain adaptation, transductive learning)
- `labeled`: Labeled test-participant data (calibration, fine-tuning, few-shot)
- `na`: Not applicable
- `unclear`: Unclear

### `M1`
How were hyperparameters, features or the stopping epoch chosen?
Shown when: `X1=yes`
Decision rule: Consider hyperparameters, feature selection or ranking, and the stopping epoch together, and code the least safe answer that applies, in this order: using test data, not reported, inside the training set, fixed. Values listed without saying how they were chosen count as Not reported, not as Fixed.
Options:
- `fixed`: Fixed in advance or taken from prior work
- `inner`: On data inside the training set (validation split or nested cross-validation)
- `test`: Using test data (for example the best epoch on the test folds, or features ranked on the whole dataset before the split)
- `not_reported`: Not reported


## Code stage, Participant-independent evidence and claims

### `R1` (primary)
Does the paper's own EEG-only work on DEAP, DREAMER or a SEED-family dataset include a participant-disjoint result?
Shown when: `X1=yes`
Decision rule: Consider every EEG-only emotion result from the paper's own experiments on those datasets, including tables and supplements. Baselines the authors re-ran count; numbers quoted from other papers, multimodal results and results on other datasets do not. Yes if any of them meets the S2 definition. Otherwise Unclear if any of them might meet it but its split cannot be determined. Otherwise No. When the headline result is itself such a result, R1 is Yes whenever S2 is Yes, and is never No when S2 is Unclear.
Options:
- `yes`: Yes
- `no`: No
- `unclear`: Unclear

### `R2`
Best participant-disjoint value
Shown when: `X1=yes & R1=yes`
Decision rule: The best participant-disjoint value counted under R1, for the proposed method or, when the paper proposes none, for any method the authors ran, on the headline dataset and task and in the headline metric. If no such value exists, leave it blank and explain in the note; do not substitute another dataset, task or metric.

### `R3`
Normalization scope for that participant-disjoint result
Shown when: `X1=yes & R1=yes`
Decision rule: The N1 options applied to the result in R2, or to the best participant-disjoint result when R2 is blank. If that result is the headline result, repeat your N1 answer.
Options:
- `none`: None described
- `instance`: Per window or per trial only (for example baseline subtraction within a trial)
- `train_only`: Fit on training data only
- `participant_all`: Per participant, session or recording, over all of that data
- `dataset_all`: Over the whole dataset before the split
- `unclear`: Mentioned, but the scope cannot be determined

### `R4`
Test-participant data used for that participant-disjoint result
Shown when: `X1=yes & R1=yes`
Decision rule: The T1 options applied to the same result. Not applicable does not arise here, because the result is participant-disjoint.
Options:
- `none`: No
- `unlabeled`: Unlabeled test-participant data (domain adaptation, transductive learning)
- `labeled`: Labeled test-participant data (calibration, fine-tuning, few-shot)
- `na`: Not applicable
- `unclear`: Unclear

### `C1` (primary)
Does the paper make a population-level claim?
Shown when: `X1=yes`
Decision rule: Code from the title, abstract and conclusion only, regardless of how the evaluation was done. Explicit: says the method works for new, unseen or other people, or calls it subject-independent, cross-subject, user-independent or generalizable across individuals. Generic: a performance or capability statement about the method, for example that it achieves 95% accuracy for EEG-based emotion recognition, that is not limited to the participants it was trained on. No: every such statement is explicitly limited to within-subject, subject-dependent, personalized or calibrated use, or the paper makes no such statement. A title that only names the topic is not a performance statement. A qualifier such as subject-dependent limits only the statement it belongs to. If statements differ, code the strongest: Explicit over Generic over No.
Options:
- `explicit`: Explicit population claim
- `generic`: Generic population wording
- `no`: No population claim


## Code stage, Evidence

Quotes let the adjudicator settle disagreements without reopening the paper. Include the page or section.

### `Q_split`
Quote for the evaluation design (S1 to S5, U1)

### `Q_norm`
Quote for normalization and test-participant data (N1, T1, R3, R4)

### `Q_claim`
Quote for the population claim (C1)

### `note`
Note

### `minutes`
Minutes spent on this paper
