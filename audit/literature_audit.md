# Literature audit — subject-identity leakage in affective EEG (DEAP/SEED/DREAMER)

**33 emotion-EEG papers** coded (plus 9 survey/methodology anchors).

## Headline tally
- **21/33 (63%)** provide *no leak-free subject-independent population evidence* (subject-dependent, subject-pooled, or unclear-scope protocols).
- **7/33** carry **High** subject-identity leakage risk (pooled or segment-level k-fold).
- The **12** papers with clean subject-independent / cross-dataset evaluation report markedly lower accuracy (~0.51-0.73), and the most conservative benchmark (Kukhilava 2025) is near chance.

## Coding rubric
High = subjects pooled / segment-level k-fold (identity or near-duplicate windows in train+test). Medium = subject-dependent only, or unclear split/normalization scope. Low = clean LOSO / cross-dataset, train-only normalization, trial/subject unit. `confidence`: high = verified from text/primary source; med/low = inferred from abstract (confirm vs full text).

## Coded papers

| paper_id | year | venue | datasets | model_family | eval_protocol | statistical_unit | headline_metric | subject_independent_eval | leakage_risk | confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| Koelstra2012 | 2012 | IEEE Trans. Affective Computing | DEAP | classical (Gaussian NB) | subject-dependent (leave-one-trial-out) | trial | F1 0.58-0.62 | none | Medium | high |
| Zheng2015 | 2015 | IEEE Trans. Autonomous Mental Development | SEED | DBN | subject-dependent (within-session split) | segment (DE, 1s) | acc 0.86 | none | Medium | med |
| Katsigiannis2018 | 2018 | IEEE J. Biomedical and Health Informatics | DREAMER | classical (SVM) | subject-dependent (leave-one-out) | trial/segment | acc ~0.62 | none | Medium | med |
| Alhagry2017 | 2017 | IJACSA | DEAP | RNN-LSTM | subject-dependent (per-participant, segment split) | segment | acc 0.85 | none | High | high |
| Tripathi2017 | 2017 | AAAI/IAAI | DEAP | CNN/DNN | mixed-subject pooled (random split) | sample/segment | acc 0.75 val / 0.81 aro | none | High | med |
| YangCNNRNN2018 | 2018 | IJCNN / Neurocomputing | DEAP | CNN-RNN | subject-dependent / mixed (segment CV) | segment | acc ~0.90 | none | High | low |
| Song2018 | 2018 | IEEE Trans. Affective Computing | SEED, DREAMER | GNN | subject-dependent (primary) + some subject-independent | segment (DE) | SEED 0.904 subj-dep | partial | Medium | high |
| Zhong2020 | 2020 | IEEE Trans. Affective Computing | SEED, SEED-IV | GNN | subject-dependent + subject-independent (LOSO) | segment (DE, 1s) | SEED 0.949 subj-dep / 0.853 LOSO | primary | Low | high |
| Li2018hcnn | 2018 | Cognitive Computation | SEED | CNN | subject-dependent (within-subject CV) | segment | acc ~0.88 | none | Medium | low |
| Li2018bidann | 2018 | IEEE Trans. Affective Computing | SEED | domain-adversarial NN | subject-independent (LOSO) | segment (DE) | SEED ~0.923 LOSO | primary | Low | high |
| Li2020r2g | 2020 | IEEE Trans. Affective Computing | SEED | RNN/GNN | subject-dependent + subject-independent | segment | SEED ~0.93 | partial | Medium | low |
| Tao2020 | 2020 | IEEE Trans. Affective Computing | DEAP | CNN-RNN + attention | subject-dependent (10-fold over segments) | segment | val 0.937 / aro 0.934 | none | High | high |
| Cui2020 | 2020 | Knowledge-Based Systems | DEAP | CNN | subject-dependent (segment CV) | segment | acc ~0.97 | none | High | low |
| Wang2018plv | 2018 | (journal) | DEAP | GNN | subject-dependent (segment CV) | segment | acc ~0.84 | none | Medium | low |
| Ding2022 | 2022 | IEEE Trans. Affective Computing | DEAP, MAHNOB-HCI | CNN | subject-dependent (leave-trials-out) | trial | DEAP ~0.62-0.63 | none | Medium | med |
| Jia2020 | 2020 | ACM Multimedia | SEED, DEAP | CNN-attention | subject-dependent (within-subject CV) | segment | SEED ~0.96 | none | Medium | low |
| Zhang2020gcb | 2020 | IEEE Trans. Affective Computing | SEED, DREAMER | GNN | subject-dependent (within-subject CV) | segment | SEED ~0.94 | none | Medium | low |
| Du2022 | 2022 | IEEE Trans. Affective Computing | SEED, SEED-IV, DEAP | RNN-LSTM + attention | subject-dependent + cross-subject transfer | segment | varies | partial | Medium | low |
| Topic2021 | 2021 | (journal) | DEAP, SEED, DREAMER | CNN (topographic/holographic maps) | subject-dependent (+ some independent) | segment | 0.85-0.95 | partial | Medium | low |
| Tuncer2021 | 2021 | (journal) | DREAMER, DEAP | classical | subject-dependent / mixed (10-fold over samples) | sample | acc >0.95 | none | High | low |
| Song2021iag | 2021 | (journal) | SEED | GNN | subject-dependent + cross-subject | segment | SEED ~0.95 | partial | Medium | low |
| Liu2021_3dcnn | 2021 | (journal) | DEAP, SEED | CNN (3D) | subject-dependent (segment CV) | segment | acc ~0.93 | none | High | low |
| Rayatdoost2018 | 2018 | IEEE MLSP | DEAP, MAHNOB, +own | CNN (spectral topomaps) | cross-corpus / subject-independent | segment | sharp drop across corpora | primary | Low | high |
| Cimtay2020 | 2020 | Sensors | DEAP, SEED, LUMED | CNN (InceptionResNetV2) | cross-subject + cross-dataset | segment | DEAP cross-subj 0.728; SEED->DEAP 0.581 | primary | Low | high |
| Pandey2022 | 2019 | Springer (LNNS) / journal | DEAP | DNN (VMD features) | subject-independent (LOSO) | trial/segment | val 0.625 / aro 0.613 | primary | Low | high |
| Lan2018 | 2018 | IEEE Trans. Cognitive and Developmental Systems | SEED, DEAP | domain adaptation (classical) | cross-subject (domain adaptation) | segment | cross-subject improvement | primary | Low | med |
| Li2020_multisource | 2020 | IEEE Trans. Cybernetics | SEED | transfer learning | cross-subject | segment | +12.7% on SEED | primary | Low | high |
| Tang2023 | 2023 | Biomed. Signal Process. & Control | DEAP | CNN | subject-independent (LOSO) | trial/segment | aro 0.683 / val 0.675 | primary | Low | high |
| Wang2024_ssl | 2024 | arXiv preprint | DEAP | self-supervised | subject-independent (LOSO, no target FT) | trial | aro 0.697 / val 0.655 | primary | Low | high |
| Kukhilava2025 | 2025 | arXiv preprint | DEAP, + | CNN family (EEGNet/TSception/Deep/ShallowConvNet) | subject-independent (LOSO) | trial | aro 0.53-0.57 / val 0.51-0.53 | primary | Low | high |
| Zhang2025_mdjpt | 2025 | NeurIPS | 6 emotion datasets incl. DEAP | Transformer (pretrain) | cross-dataset (zero/few-shot) | segment | few-shot +4.57% AUROC | primary | Low | med |
| Jiang2024_labram | 2024 | ICLR | many incl. emotion | Transformer (foundation model) | cross-subject (pretrain+finetune) | segment | downstream gains | partial | Medium | med |
| Yang2023_biot | 2023 | NeurIPS | cross-dataset biosignals | Transformer | cross-data | segment | cross-data gains | primary | Low | med |

## Context references (surveys & leakage-methodology anchors)

| paper_id | year | venue | notes |
|---|---|---|---|
| Apicella2024 | 2024 | Neurocomputing | Systematic review of generalization; directly supports the argument |
| Craik2019 | 2019 | J. Neural Engineering | Field review (target venue) |
| Roy2019 | 2019 | J. Neural Engineering | Field review (target venue) |
| Suhaimi2020 | 2020 | Computational Intelligence and Neuroscience | Emotion-EEG review |
| Saeb2017 | 2017 | GigaScience | Canonical record-wise-vs-subject-wise CV leakage warning |
| Little2017 | 2017 | GigaScience | CV strategy / leakage in biomedical ML |
| Varoquaux2018 | 2018 | NeuroImage | CV instability in neuroimaging |
| Poldrack2020 | 2020 | JAMA Psychiatry | Best practice for predictive neuro models |
| Kaufman2012 | 2012 | ACM Trans. KDD | Foundational data-leakage taxonomy |
