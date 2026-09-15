"""
Recompute audit statistics from literature_audit.csv for the reworked perspective:
- tallies by leakage risk and by CODING CONFIDENCE (the 'unclear reporting' dimension,
  reported separately rather than folded into medium risk);
- the SEED vs DEAP/DREAMER split among clean subject-independent papers;
- medians/distributions of clean subject-independent accuracy where a number is reported;
- a complete LaTeX supplementary table of all coded emotion-EEG papers.
Everything is derived from the real coded data; no numbers are invented.
"""
import csv, statistics
from pathlib import Path

d = Path(__file__).resolve().parent
rows = list(csv.DictReader(open(d / "literature_audit.csv")))
emo = [r for r in rows if r["category"] in ("dataset", "primary", "honest")]

def tally(key):
    out = {}
    for r in emo:
        out[r[key]] = out.get(r[key], 0) + 1
    return out

print("total emotion-EEG papers:", len(emo))
print("by leakage_risk:", tally("leakage_risk"))
print("by coding confidence:", tally("confidence"))
print("by subject_independent_eval:", tally("subject_independent_eval"))

# no clean subject-independent evidence = SI none, or risk High/Medium
def no_clean(r):
    return r["subject_independent_eval"] == "none" or r["leakage_risk"] in ("High", "Medium")
leaky = [r for r in emo if no_clean(r)]
clean = [r for r in emo if not no_clean(r)]
print(f"no clean SI: {len(leaky)}/{len(emo)} ({round(100*len(leaky)/len(emo))}%)")
print("clean SI papers:", [r["paper_id"] for r in clean])

# unclear reporting = low coding confidence (protocol inferred, not verified from text)
unclear = [r for r in emo if r["confidence"] == "low"]
print(f"low-confidence / unclear-reporting: {len(unclear)}/{len(emo)}  ->", [r["paper_id"] for r in unclear])

# clean SI split by paradigm, with hand-parsed reported numbers (only where a value is stated)
seed_vals = {"Li2018bidann": 0.923, "Zhong2020": 0.853}  # SEED discrete-emotion LOSO
deap_va = {  # DEAP/DREAMER video valence/arousal, leak-free; (valence, arousal) where given
    "Cimtay2020": [0.728],            # cross-subject DEAP (also 0.581 cross-dataset)
    "Pandey2022": [0.625, 0.613],
    "Tang2023": [0.675, 0.683],
    "Wang2024_ssl": [0.655, 0.697],
    "Kukhilava2025": [0.52, 0.55],    # midpoints of reported 0.51-0.53 / 0.53-0.57
}
deap_all = [v for vs in deap_va.values() for v in vs]
print("\nSEED discrete-emotion clean LOSO:", seed_vals, "-> range", min(seed_vals.values()), "to", max(seed_vals.values()))
print("DEAP/DREAMER video V/A clean SI values:", sorted(deap_all))
print(f"  median={statistics.median(deap_all):.3f}  min={min(deap_all):.3f}  max={max(deap_all):.3f}")

# ---- LaTeX supplementary longtable of all coded emotion-EEG papers ----
# paper_id -> references.bib key, so the audit rows enter the reference list instead of
# printing as bare author-year text. Every emotion-EEG row must map to a real cited key.
BIBKEY = {
    "Koelstra2012": "koelstra2012deap", "Zheng2015": "zheng2015seed",
    "Katsigiannis2018": "katsigiannis2018dreamer", "Alhagry2017": "alhagry2017lstm",
    "Tripathi2017": "tripathi2017deap", "YangCNNRNN2018": "yang2018cnnrnn",
    "Song2018": "song2018dgcnn", "Zhong2020": "zhong2020rgnn", "Li2018hcnn": "li2018hcnn",
    "Li2018bidann": "li2018bidann", "Li2020r2g": "li2020r2g", "Tao2020": "tao2020acrnn",
    "Cui2020": "cui2020racnn", "Wang2018plv": "wang2018plv", "Ding2022": "ding2022tsception",
    "Jia2020": "jia2020sst", "Zhang2020gcb": "zhang2020gcb", "Du2022": "du2022atdd",
    "Topic2021": "topic2021", "Tuncer2021": "tuncer2021", "Song2021iag": "song2021iag",
    "Liu2021_3dcnn": "liu2021_3dcnn", "Rayatdoost2018": "rayatdoost2018crosscorpus",
    "Cimtay2020": "cimtay2020", "Pandey2022": "pandey2019subjectindependent",
    "Lan2018": "lan2018da", "Li2020_multisource": "li2020multisource", "Tang2023": "tang2023stiln",
    "Wang2024_ssl": "wang2024cascaded", "Kukhilava2025": "kukhilava2025benchmark",
    "Zhang2025_mdjpt": "zhang2025mdjpt", "Jiang2024_labram": "jiang2024labram",
    "Yang2023_biot": "yang2023biot",
}
missing = [r["paper_id"] for r in emo if r["paper_id"] not in BIBKEY]
assert not missing, f"audit rows with no bib key: {missing}"

def esc(s):
    return s.replace("&", "\\&").replace("_", "\\_").replace("%", "\\%")
def study_cell(r):
    # first author + \cite so the study is findable in the reference list
    first = esc(r["citation"].split(",")[0].split(" et al")[0].split(" &")[0].strip())
    return f"{first} \\cite{{{BIBKEY[r['paper_id']]}}}"
lines = [
 r"% Auto-generated from literature_audit.csv by build_audit_supplement.py -- do not hand-edit.",
 r"\footnotesize",
 r"\begin{longtable}{@{}p{2.3cm}cp{1.5cm}p{2.3cm}p{1.2cm}p{2.1cm}ccc@{}}",
 r"\caption{Complete audit of the 33 emotion-EEG studies (dataset anchors, method papers, and clean "
 r"subject-independent baselines). Two axes are graded separately. \emph{Risk} grades the SPLIT only: whether "
 r"participants bridge the train/test boundary. \emph{Norm.\ class} grades the normalization scope on its own "
 r"axis, because a subject-independent split can still be compromised by normalization statistics estimated from "
 r"the held-out participant's own recording; per-subject normalization is therefore not treated as automatically "
 r"clean, and rows marked ``scope unverified'' are those whose normalization we could not confirm from the text. "
 r"Coding confidence is graded high (verified from the full text), medium (partly verified) or low (inferred from "
 r"the abstract); the low-confidence rows constitute the ``unclear reporting'' stratum and are reported separately "
 r"from leakage risk rather than folded into it. This is a purposive, single-coder sample and the counts describe "
 r"it rather than the field. The full machine-readable coding sheet, including per-paper notes, is released with "
 r"the code.}\label{tab:audit-full}\\",
 r"\toprule",
 r"Study & Yr & Dataset & Protocol & Unit & Norm.\ class & SI eval & Risk & Conf. \\",
 r"\midrule\endfirsthead",
 r"\multicolumn{9}{c}{\tablename~\thetable\ (continued)}\\ \toprule",
 r"Study & Yr & Dataset & Protocol & Unit & Norm.\ class & SI eval & Risk & Conf. \\ \midrule\endhead",
 r"\midrule \multicolumn{9}{r}{\textit{continued on next page}}\\ \endfoot",
 r"\bottomrule\endlastfoot",
]
for r in emo:
    cells = [study_cell(r), r["year"],
             esc(r["datasets"]), esc(r["eval_protocol"]),
             esc(r["statistical_unit"]), esc(r.get("normalization_class", r["normalization_scope"])),
             r["subject_independent_eval"], r["leakage_risk"], r["confidence"]]
    lines.append(" & ".join(cells) + r" \\")
lines.append(r"\end{longtable}")
lines.append(r"\normalsize")
(d / "audit_supplement_table.tex").write_text("\n".join(lines) + "\n")
print("\nwrote audit_supplement_table.tex")
