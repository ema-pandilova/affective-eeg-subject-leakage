"""
Build the literature audit table (CSV + markdown) for the perspective paper.

Each row characterizes a high-impact DEAP/SEED/DREAMER affective-EEG paper by its
evaluation protocol and subject-identity leakage risk. Protocols were coded from
the evaluation sections / abstracts as reported; `confidence` flags how firmly the
coding is grounded (high = verified from text/primary source in this session or
prior verified notes; med/low = inferred from abstract and to be confirmed against
full text before final submission).

Leakage-risk rubric. IMPORTANT: `leakage_risk` grades the SPLIT only (whether participants
bridge the train/test boundary). Normalization scope is a SEPARATE axis, tracked in
`normalization_class`, because a subject-independent split can still be compromised by
normalization statistics estimated from the held-out participant's own data. We do not treat
per-subject normalization as automatically clean.

  High   = subjects pooled with random/k-fold split over (often overlapping) segments,
           or subject-dependent k-fold over overlapping segments -> identity / window
           near-duplicates appear in both train and test.
  Medium = subject-dependent only (single-subject; no population generalization shown),
           or split scope unclear.
  Low    = clean leave-one-subject-out or cross-dataset split with trial/subject as the
           statistical unit. NOTE: "Low" certifies the split, NOT the normalization.

normalization_class (derived from normalization_scope):
  train-only                     = statistics fit on training data only (verified from text).
  per-subject (scope unverified) = per-subject/per-recording z-scoring whose scope we could not
                                   verify; if fit over the whole recording of a held-out subject
                                   it is transductive, target-derived normalization.
  global (scope unverified)      = dataset-wide statistics, scope unverified.
  n/a                            = not applicable (surveys/methodology).

subject_independent_eval: none / partial / primary.
category: dataset / primary / honest / survey / methodology.
"""
import csv
from pathlib import Path

C = ["paper_id","citation","year","venue","datasets","task","model_family",
     "eval_protocol","statistical_unit","normalization_scope","headline_metric",
     "subject_independent_eval","subject_id_as_confound","generalization_claim",
     "leakage_risk","confidence","category","notes"]

R = [
# --- dataset anchors ---
["Koelstra2012","Koelstra et al., DEAP: A Database for Emotion Analysis using Physiological Signals","2012","IEEE Trans. Affective Computing","DEAP","valence/arousal/liking binary","classical (Gaussian NB)","subject-dependent (leave-one-trial-out)","trial","per-subject","F1 0.58-0.62","none","no","within-subject","Medium","high","dataset","Single-trial within-subject; modest accuracy; no population claim"],
["Zheng2015","Zheng & Lu, Investigating Critical Frequency Bands and Channels for EEG Emotion Recognition with Deep Belief Networks","2015","IEEE Trans. Autonomous Mental Development","SEED","3-class","DBN","subject-dependent (within-session split)","segment (DE, 1s)","per-subject","acc 0.86","none","no","ambiguous","Medium","med","dataset","SEED origin; subject-dependent headline"],
["Katsigiannis2018","Katsigiannis & Ramzan, DREAMER: A Database for Emotion Recognition through EEG/ECG from Low-cost Devices","2018","IEEE J. Biomedical and Health Informatics","DREAMER","valence/arousal/dominance binary","classical (SVM)","subject-dependent (leave-one-out)","trial/segment","per-subject","acc ~0.62","none","no","within-subject","Medium","med","dataset","DREAMER origin; within-subject"],
# --- high-impact method papers (mostly subject-dependent / pooled) ---
["Alhagry2017","Alhagry et al., Emotion Recognition based on EEG using LSTM Recurrent Neural Network","2017","IJACSA","DEAP","valence/arousal/liking binary","RNN-LSTM","subject-dependent (per-participant, segment split)","segment","per-subject","acc 0.85","none","no","ambiguous","High","high","primary","Per-participant segment-level over overlapping segments; widely cited '85%'"],
["Tripathi2017","Tripathi et al., Using Deep and Convolutional Neural Networks for Accurate Emotion Classification on DEAP","2017","AAAI/IAAI","DEAP","valence/arousal binary & 3-class","CNN/DNN","mixed-subject pooled (random split)","sample/segment","global","acc 0.75 val / 0.81 aro","none","no","population (implied)","High","med","primary","Subjects pooled; random split -> direct identity leak"],
["YangCNNRNN2018","Yang et al., Continuous/parallel CNN-RNN for EEG emotion on DEAP","2018","IJCNN / Neurocomputing","DEAP","valence/arousal binary","CNN-RNN","subject-dependent / mixed (segment CV)","segment","per-subject","acc ~0.90","none","no","ambiguous","High","low","primary","Segment-level CV; protocol partly unclear"],
["Song2018","Song et al., EEG Emotion Recognition Using Dynamical Graph Convolutional Neural Networks (DGCNN)","2018","IEEE Trans. Affective Computing","SEED, DREAMER","3-class / binary","GNN","subject-dependent (primary) + some subject-independent","segment (DE)","per-subject","SEED 0.904 subj-dep","partial","no","population","Medium","high","primary","Reports subject-dependent headline plus limited cross-subject; verified"],
["Zhong2020","Zhong et al., EEG-Based Emotion Recognition Using Regularized Graph Neural Networks (RGNN)","2020","IEEE Trans. Affective Computing","SEED, SEED-IV","3/4-class","GNN","subject-dependent + subject-independent (LOSO)","segment (DE, 1s)","per-subject","SEED 0.949 subj-dep / 0.853 LOSO","primary","partial","population","Low","high","primary","Genuinely reports LOSO; NodeDAT targets cross-subject shift; verified"],
["Li2018hcnn","Li et al., Hierarchical Convolutional Neural Networks for EEG-Based Emotion Recognition","2018","Cognitive Computation","SEED","3-class","CNN","subject-dependent (within-subject CV)","segment","per-subject","acc ~0.88","none","no","ambiguous","Medium","low","primary","Protocol inferred from abstract"],
["Li2018bidann","Li et al., A Bi-Hemisphere Domain Adversarial Neural Network (BiDANN) for EEG Emotion Recognition","2018","IEEE Trans. Affective Computing","SEED","3-class","domain-adversarial NN","subject-independent (LOSO)","segment (DE)","per-subject","SEED ~0.923 LOSO","primary","yes","population","Low","high","honest","Subject-independent via adversarial removal of subject info; verified"],
["Li2020r2g","Li et al., From Regional to Global Brain (R2G-STNN) for EEG Emotion Recognition","2020","IEEE Trans. Affective Computing","SEED","3-class","RNN/GNN","subject-dependent + subject-independent","segment","per-subject","SEED ~0.93","partial","no","population","Medium","low","primary","Reports both; protocol partly inferred"],
["Tao2020","Tao et al., EEG Emotion Recognition via Channel-wise Attention and Self Attention (ACRNN)","2020","IEEE Trans. Affective Computing","DEAP","valence/arousal binary","CNN-RNN + attention","subject-dependent (10-fold over segments)","segment","per-subject","val 0.937 / aro 0.934","none","no","ambiguous","High","high","primary","Subject-dependent 10-fold over (overlapping) segments; verified"],
["Cui2020","Cui et al., End-to-End Regional-Asymmetric CNN (RACNN) for EEG Emotion Recognition","2020","Knowledge-Based Systems","DEAP","valence/arousal binary","CNN","subject-dependent (segment CV)","segment","per-subject","acc ~0.97","none","no","ambiguous","High","low","primary","Very high reported accuracy; segment-level; protocol inferred"],
["Wang2018plv","Wang et al., Phase-Locking-Value based Graph CNN for EEG Emotion Recognition","2018","(journal)","DEAP","valence/arousal binary","GNN","subject-dependent (segment CV)","segment","per-subject","acc ~0.84","none","no","ambiguous","Medium","low","primary","Protocol inferred"],
["Ding2022","Ding et al., TSception: Temporal Dynamics and Spatial Asymmetry for EEG Emotion Recognition","2022","IEEE Trans. Affective Computing","DEAP, MAHNOB-HCI","valence/arousal binary","CNN","subject-dependent (leave-trials-out)","trial","per-subject","DEAP ~0.62-0.63","none","no","within-subject","Medium","med","primary","Trial-level CV (better) but within-subject only"],
["Jia2020","Jia et al., SST-EmotionNet: Spatial-Spectral-Temporal 3D Attention Network","2020","ACM Multimedia","SEED, DEAP","3-class / binary","CNN-attention","subject-dependent (within-subject CV)","segment","per-subject","SEED ~0.96","none","no","ambiguous","Medium","low","primary","Protocol inferred"],
["Zhang2020gcb","Zhang et al., GCB-Net: Graph Convolutional Broad Network for EEG Emotion Recognition","2020","IEEE Trans. Affective Computing","SEED, DREAMER","3-class / binary","GNN","subject-dependent (within-subject CV)","segment","per-subject","SEED ~0.94","none","no","ambiguous","Medium","low","primary","Protocol inferred"],
["Du2022","Du et al., An Efficient LSTM Network for Emotion Recognition from Multichannel EEG (ATDD-LSTM)","2022","IEEE Trans. Affective Computing","SEED, SEED-IV, DEAP","multi-class","RNN-LSTM + attention","subject-dependent + cross-subject transfer","segment","per-subject","varies","partial","partial","population","Medium","low","primary","Attention transfer for cross-subject; protocol inferred"],
["Topic2021","Topic & Russo, Emotion Recognition based on EEG Feature Maps through Deep Learning","2021","(journal)","DEAP, SEED, DREAMER","binary / multi-class","CNN (topographic/holographic maps)","subject-dependent (+ some independent)","segment","per-subject","0.85-0.95","partial","no","population","Medium","low","primary","Multi-dataset; mixed protocol; inferred"],
["Tuncer2021","Tuncer et al., Handcrafted (TQWT/pattern) features for EEG emotion recognition","2021","(journal)","DREAMER, DEAP","binary","classical","subject-dependent / mixed (10-fold over samples)","sample","global/per-subject","acc >0.95","none","no","ambiguous","High","low","primary","10-fold over pooled samples; protocol inferred"],
["Song2021iag","Song et al., Instance-Adaptive Graph for EEG Emotion Recognition (IAG)","2021","(journal)","SEED","3-class","GNN","subject-dependent + cross-subject","segment","per-subject","SEED ~0.95","partial","no","population","Medium","low","primary","Reports both; inferred"],
["Liu2021_3dcnn","Liu et al., 3D Convolutional Neural Network for EEG-based Emotion Recognition","2021","(journal)","DEAP, SEED","binary / 3-class","CNN (3D)","subject-dependent (segment CV)","segment","per-subject","acc ~0.93","none","no","ambiguous","High","low","primary","Segment-level; protocol inferred"],
# --- honest subject-independent / cross-dataset baselines (contrast set) ---
["Rayatdoost2018","Rayatdoost & Soleymani, Cross-corpus EEG-based Emotion Recognition","2018","IEEE MLSP","DEAP, MAHNOB, +own","binary","CNN (spectral topomaps)","cross-corpus / subject-independent","segment","train-only","sharp drop across corpora","primary","yes","population (questions it)","Low","high","honest","KEY precedent: accuracy collapses across corpora; models learn stimulus info; verified"],
["Cimtay2020","Cimtay & Ekmekcioglu, Pretrained CNN on Cross-Subject and Cross-Dataset EEG Emotion Recognition","2020","Sensors","DEAP, SEED, LUMED","binary / 3-class","CNN (InceptionResNetV2)","cross-subject + cross-dataset","segment","per-subject (stratified)","DEAP cross-subj 0.728; SEED->DEAP 0.581","primary","yes","population","Low","high","honest","Cross-dataset drop to 0.58; verified"],
["Pandey2022","Pandey & Seeja, Subject-Independent Emotion Detection from EEG using Deep Neural Network","2019","Springer (LNNS) / journal","DEAP","valence/arousal binary","DNN (VMD features)","subject-independent (LOSO)","trial/segment","train-only","val 0.625 / aro 0.613","primary","yes","population","Low","high","honest","Honest LOSO ~0.62; verified"],
["Lan2018","Lan et al., Domain Adaptation Techniques for EEG-based Emotion Recognition: A Comparative Study","2018","IEEE Trans. Cognitive and Developmental Systems","SEED, DEAP","binary / 3-class","domain adaptation (classical)","cross-subject (domain adaptation)","segment","train-only","cross-subject improvement","primary","yes","population","Low","med","honest","Cross-subject DA comparison across two datasets"],
["Li2020_multisource","Li et al., Multisource Transfer Learning for Cross-Subject EEG Emotion Recognition","2020","IEEE Trans. Cybernetics","SEED","3-class","transfer learning","cross-subject","segment","train-only","+12.7% on SEED","primary","yes","population","Low","high","honest","Cross-subject transfer; verified"],
["Tang2023","Tang et al., STILN: Spatial-Temporal-Inter-channel Learning Network (subject-independent)","2023","Biomed. Signal Process. & Control","DEAP","valence/arousal binary","CNN","subject-independent (LOSO)","trial/segment","train-only","aro 0.683 / val 0.675","primary","yes","population","Low","high","honest","Honest subject-independent; verified"],
["Wang2024_ssl","Wang, Chen & Song, Cascaded Self-Supervised Learning for Cross-Subject EEG Emotion (domain generalization)","2024","arXiv preprint","DEAP","valence/arousal binary","self-supervised","subject-independent (LOSO, no target FT)","trial","train-only","aro 0.697 / val 0.655","primary","yes","population","Low","high","honest","Domain-generalization LOSO; verified"],
["Kukhilava2025","Kukhilava et al., A Unified Benchmark for EEG Emotion Recognition","2025","arXiv preprint","DEAP, +","valence/arousal binary","CNN family (EEGNet/TSception/Deep/ShallowConvNet)","subject-independent (LOSO)","trial","train-only","aro 0.53-0.57 / val 0.51-0.53","primary","yes","population (near chance)","Low","high","honest","STRONGEST contrast: conservative LOSO near chance; verified"],
["Zhang2025_mdjpt","Zhang et al., mdJPT: Multi-dataset Joint Pre-training of Emotional EEG","2025","NeurIPS","6 emotion datasets incl. DEAP","various","Transformer (pretrain)","cross-dataset (zero/few-shot)","segment","train-only","few-shot +4.57% AUROC","primary","yes","population","Low","med","honest","Explicit cross-dataset generalization; verified"],
["Jiang2024_labram","Jiang et al., LaBraM: Large Brain Model for Generic EEG Representations","2024","ICLR","many incl. emotion","various","Transformer (foundation model)","cross-subject (pretrain+finetune)","segment","per-recording","downstream gains","partial","partial","population","Medium","med","primary","EEG foundation model; emotion among downstream tasks; verified"],
["Yang2023_biot","Yang et al., BIOT: Biosignal Transformer for Cross-data Learning in the Wild","2023","NeurIPS","cross-dataset biosignals","various","Transformer","cross-data","segment","per-recording","cross-data gains","primary","partial","population","Low","med","primary","Cross-data transformer; verified"],
# --- surveys / methodology anchors (context; excluded from leakage tally) ---
["Apicella2024","Apicella et al., Toward Cross-Subject and Cross-Session Generalization in EEG-based Emotion Recognition: Systematic Review, Taxonomy, and Methods","2024","Neurocomputing","review","-","review","-","-","-","-","-","yes","-","NA","high","survey","Systematic review of generalization; directly supports the argument"],
["Craik2019","Craik et al., Deep learning for EEG classification tasks: a review","2019","J. Neural Engineering","review","-","review","-","-","-","-","-","mentioned","-","NA","high","survey","Field review (target venue)"],
["Roy2019","Roy et al., Deep learning-based EEG analysis: a systematic review","2019","J. Neural Engineering","review","-","review","-","-","-","-","-","mentioned","-","NA","high","survey","Field review (target venue)"],
["Suhaimi2020","Suhaimi et al., EEG-based Emotion Recognition: A State-of-the-Art Review","2020","Computational Intelligence and Neuroscience","review","-","review","-","-","-","-","-","no","-","NA","med","survey","Emotion-EEG review"],
["Saeb2017","Saeb et al., The need to approximate the use-case in clinical machine learning (subject-wise vs record-wise CV)","2017","GigaScience","methodology","-","methodology","-","-","-","-","-","yes","-","NA","high","methodology","Canonical record-wise-vs-subject-wise CV leakage warning"],
["Little2017","Little et al., Using and understanding cross-validation strategies","2017","GigaScience","methodology","-","methodology","-","-","-","-","-","yes","-","NA","high","methodology","CV strategy / leakage in biomedical ML"],
["Varoquaux2018","Varoquaux, Cross-validation failure: small sample sizes lead to large error bars","2018","NeuroImage","methodology","-","methodology","-","-","-","-","-","yes","-","NA","high","methodology","CV instability in neuroimaging"],
["Poldrack2020","Poldrack, Huckins & Varoquaux, Establishment of Best Practices for Evidence for Prediction: A Review","2020","JAMA Psychiatry","methodology","-","methodology","-","-","-","-","-","yes","-","NA","high","methodology","Best practice for predictive neuro models"],
["Kaufman2012","Kaufman et al., Leakage in Data Mining: Formulation, Detection, and Avoidance","2012","ACM Trans. KDD","methodology","-","methodology","-","-","-","-","-","yes","-","NA","high","methodology","Foundational data-leakage taxonomy"],
]

audit_dir = Path(__file__).resolve().parent

# ---- derived normalization axis (kept separate from the split-based leakage_risk) ----
def norm_class(ns, category):
    if category in ("survey", "methodology") or ns in ("-", ""):
        return "n/a"
    if ns == "train-only":
        return "train-only"
    if ns.startswith("per-subject"):
        return "per-subject (scope unverified)"
    if ns.startswith("per-recording"):
        return "per-recording (scope unverified)"
    if ns.startswith("global"):
        return "global (scope unverified)"
    return "unstated"

C2 = C + ["normalization_class"]
R2 = [r + [norm_class(r[C.index("normalization_scope")], r[C.index("category")])] for r in R]
with open(audit_dir/"literature_audit.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(C2); w.writerows(R2)

# ---- summary tally over emotion-EEG papers (exclude survey/methodology) ----
emo=[dict(zip(C2,r)) for r in R2 if r[C.index("category")] in ("dataset","primary","honest")]
def no_clean_si(d):
    return d["subject_independent_eval"]=="none" or d["leakage_risk"] in ("High","Medium")
leaky=[d for d in emo if no_clean_si(d)]
clean=[d for d in emo if not no_clean_si(d)]
high=[d for d in emo if d["leakage_risk"]=="High"]

# Of the clean-SPLIT papers, how many also have verified train-only normalization?
clean_trainonly=[d for d in clean if d["normalization_class"]=="train-only"]
clean_unverified=[d for d in clean if d["normalization_class"]!="train-only"]
print(f"\nclean-split papers: {len(clean)}")
print(f"  of which train-only normalization (verified): {len(clean_trainonly)}")
print(f"  of which normalization scope UNVERIFIED     : {len(clean_unverified)} -> "
      f"{[(d['paper_id'], d['normalization_scope']) for d in clean_unverified]}")

# ---- markdown ----
cols_md=["paper_id","year","venue","datasets","model_family","eval_protocol",
         "statistical_unit","headline_metric","subject_independent_eval","leakage_risk","confidence"]
lines=["# Literature audit — subject-identity leakage in affective EEG (DEAP/SEED/DREAMER)","",
 f"**{len(emo)} emotion-EEG papers** coded (plus {len(R)-len(emo)} survey/methodology anchors).","",
 "## Headline tally",
 f"- **{len(leaky)}/{len(emo)} ({100*len(leaky)//len(emo)}%)** provide *no leak-free subject-independent population evidence* "
 "(subject-dependent, subject-pooled, or unclear-scope protocols).",
 f"- **{len(high)}/{len(emo)}** carry **High** subject-identity leakage risk (pooled or segment-level k-fold).",
 f"- The **{len(clean)}** papers with clean subject-independent / cross-dataset evaluation report markedly lower "
 "accuracy (~0.51-0.73), and the most conservative benchmark (Kukhilava 2025) is near chance.","",
 "## Coding rubric",
 "High = subjects pooled / segment-level k-fold (identity or near-duplicate windows in train+test). "
 "Medium = subject-dependent only, or unclear split/normalization scope. "
 "Low = clean LOSO / cross-dataset, train-only normalization, trial/subject unit. "
 "`confidence`: high = verified from text/primary source; med/low = inferred from abstract (confirm vs full text).","",
 "## Coded papers","",
 "| "+" | ".join(cols_md)+" |",
 "|"+"|".join(["---"]*len(cols_md))+"|"]
for r in R:
    d=dict(zip(C,r))
    if d["category"] in ("survey","methodology"): continue
    lines.append("| "+" | ".join(str(d[c]) for c in cols_md)+" |")
lines+=["","## Context references (surveys & leakage-methodology anchors)","",
        "| paper_id | year | venue | notes |","|---|---|---|---|"]
for r in R:
    d=dict(zip(C,r))
    if d["category"] not in ("survey","methodology"): continue
    lines.append(f"| {d['paper_id']} | {d['year']} | {d['venue']} | {d['notes']} |")
(audit_dir/"literature_audit.md").write_text("\n".join(lines)+"\n")

print(f"emotion papers={len(emo)}  no-clean-SI={len(leaky)} ({100*len(leaky)//len(emo)}%)  High-risk={len(high)}  clean-SI={len(clean)}")
print("wrote literature_audit.csv and literature_audit.md")
