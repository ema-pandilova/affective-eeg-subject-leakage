"""
Figure 1 (conceptual): why window-pooled cross-validation inflates accuracy in
affective EEG, and how leave-one-subject-out removes the effect.

Publication-style schematic: muted colourblind-aware palette, thin rules, panel
labels (a)/(b), and minimal in-figure text -- the explanation lives in the LaTeX
caption, not inside the artwork. Outputs fig1_leakage_concept.{png,pdf}.
"""
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
import matplotlib as mpl

mpl.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8.5,
    "pdf.fonttype": 42,   # embed TrueType so text stays selectable/editable
    "ps.fonttype": 42,
})

# Muted, colourblind-aware subject palette (seaborn "muted").
SUBJ = [("S1", "#4C72B0"), ("S2", "#DD8452"), ("S3", "#55A868"), ("S4", "#8172B3")]
INK, GRAY, RULE = "#1a1a1a", "#6b6b6b", "#c9c9c9"

fig = plt.figure(figsize=(7.4, 4.4))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")


def tile(x, y, w, h, c, ec="white", lw=0.6, alpha=1.0):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=c, edgecolor=ec, lw=lw, alpha=alpha))


def box(x, y, w, h, ec=GRAY, lw=0.9):
    ax.add_patch(Rectangle((x, y), w, h, facecolor="none", edgecolor=ec, lw=lw))


def txt(x, y, s, size=8.5, color=INK, ha="left", va="baseline", weight="normal", style="normal"):
    ax.text(x, y, s, fontsize=size, color=color, ha=ha, va=va, fontweight=weight, fontstyle=style)


# ------------------------------------------------------------------ top: the data
TW, TH, STEP, TGAP = 2.0, 3.0, 1.55, 2.4       # window w/h, overlap step, trial gap
row_y = [90, 85.2, 80.4, 75.6]
for (name, c), yy in zip(SUBJ, row_y):
    txt(7.5, yy + TH / 2, name, size=8, color=GRAY, ha="right", va="center")
    x = 10
    for _trial in range(3):
        for _k in range(4):                     # overlapping windows within a trial
            tile(x, yy, TW, TH, c); x += STEP
        x += TGAP

# short, neutral annotations (kept minimal; full wording goes in the caption)
ax.annotate("windows within a trial overlap\n(near-duplicate samples)",
            xy=(15.6, 92.6), xytext=(41, 92.5), fontsize=7.4, color=GRAY, va="center",
            arrowprops=dict(arrowstyle="->", lw=0.7, color=GRAY))
ax.annotate("every window carries the same\nsubject-specific signature",
            xy=(12.5, 78), xytext=(41, 78.5), fontsize=7.4, color=GRAY, va="center",
            arrowprops=dict(arrowstyle="->", lw=0.7, color=GRAY))

# dividers
ax.add_patch(FancyArrowPatch((3, 70.5), (97, 70.5), arrowstyle="-", lw=0.8, color=RULE))
ax.add_patch(FancyArrowPatch((50, 6), (50, 66), arrowstyle="-", lw=0.8, color=RULE))

# ------------------------------------------------------ (a) window-pooled k-fold
import random
random.seed(7)
txt(4, 65, "(a)", size=10, weight="bold")
txt(10.5, 65, "Window-pooled k-fold cross-validation", size=9, weight="bold")

bag = [c for (_, c) in SUBJ for _ in range(8)]
random.shuffle(bag)
txt(6, 58.4, "pool all windows, then split at random", size=7.4, color=GRAY)
i = 0
for r in range(2):
    for col in range(12):
        tile(6 + col * 3.0, 54 - r * 3.4, 2.6, 3.0, bag[i]); i += 1
ax.add_patch(FancyArrowPatch((24, 45.5), (24, 40.5), arrowstyle="-|>", mutation_scale=11,
                             lw=1.1, color=INK))

box(6, 27, 20, 10)                                        # train
txt(16, 38.2, "Train", size=7.6, color=INK, ha="center")
box(28, 27, 15, 10)                                       # test
txt(35.5, 38.2, "Test", size=7.6, color=INK, ha="center")
random.shuffle(bag)
for col in range(5):
    tile(7.5 + col * 3.6, 30, 3.0, 4.0, bag[col])
for col in range(3):
    tile(29.5 + col * 3.6, 30, 3.0, 4.0, bag[5 + col])
txt(24, 22.5, "the same subjects appear in train and test", size=7.4, color=GRAY, ha="center")
txt(24, 15.5, "AUC ≈ 0.71", size=11, weight="bold", ha="center")
txt(24, 11, "accuracy reflects who, not what", size=7.4, color=GRAY, ha="center", style="italic")

# --------------------------------------------------- (b) leave-one-subject-out
txt(53.5, 65, "(b)", size=10, weight="bold")
txt(60, 65, "Leave-one-subject-out", size=9, weight="bold")

box(56, 50, 39, 10)                                       # train S1-S3
txt(75.5, 61.2, "Train  (S1–S3)", size=7.6, color=INK, ha="center")
x = 59
for (_, c) in SUBJ[:3]:
    for _k in range(4):
        tile(x, 53, 2.5, 4.0, c); x += 2.7
    x += 2.2
ax.add_patch(FancyArrowPatch((75.5, 48.5), (75.5, 41.5), arrowstyle="-|>", mutation_scale=11,
                             lw=1.1, color=INK))

box(63, 28, 25, 10)                                       # test S4 only
txt(75.5, 39.2, "Test  (S4, unseen)", size=7.6, color=INK, ha="center")
x = 65.5
for _k in range(7):
    tile(x, 31, 2.6, 4.0, SUBJ[3][1]); x += 3.0
txt(75.5, 23.5, "the test subject is never seen in training", size=7.4, color=GRAY, ha="center")
txt(75.5, 15.5, "AUC ≈ 0.50", size=11, weight="bold", ha="center")
txt(75.5, 11, "chance — the identity shortcut is gone", size=7.4, color=GRAY, ha="center", style="italic")

fig.savefig("fig1_leakage_concept.png", dpi=300, bbox_inches="tight")
fig.savefig("fig1_leakage_concept.pdf", bbox_inches="tight")
print("wrote fig1_leakage_concept.png / .pdf")
