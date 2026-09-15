"""
Figure 1: the four-protocol decomposition.

Each row is one evaluation protocol. The strip shows the same data every time --
4 participants, 3 trials each, 4 overlapping windows per trial -- and only the
train/test assignment changes. Consecutive protocols differ in exactly one
respect, so the arrow between two rows names the single leakage channel that the
step removes, and carries the AUC it costs (DEAP valence, gradient-boosted trees).

Outputs fig1_protocol_decomposition.{png,pdf}. Supersedes make_concept_figure.py.
"""
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

mpl.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8.0,
    "pdf.fonttype": 42,   # embed TrueType so text stays selectable
    "ps.fonttype": 42,
})

TRAIN, TEST = "#4C72B0", "#DD8452"      # colourblind-aware (seaborn "muted")
INK, GRAY, FAINT = "#1a1a1a", "#6b6b6b", "#9a9a9a"

N_SUBJ, N_TRIAL, N_WIN = 4, 3, 3

# --- strip geometry ---------------------------------------------------------
X0, CELL_W, WIN_GAP, TRIAL_GAP, SUBJ_GAP = 31.0, 0.70, 0.05, 0.50, 1.30
TRIAL_W = N_WIN * CELL_W + (N_WIN - 1) * WIN_GAP
SUBJ_W = N_TRIAL * TRIAL_W + (N_TRIAL - 1) * TRIAL_GAP
CELL_H = 4.5
ROW_Y = [78.0, 60.0, 42.0, 24.0]        # bottom edge of each protocol's strip
AUC_X, ARROW_X, LABEL_X = 70.0, 76.0, 79.0

fig = plt.figure(figsize=(7.3, 5.4))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")


def cell_x(subj, trial, win):
    return X0 + subj * (SUBJ_W + SUBJ_GAP) + trial * (TRIAL_W + TRIAL_GAP) + win * (CELL_W + WIN_GAP)


def txt(x, y, s, size=8.0, color=INK, ha="left", va="center", weight="normal", style="normal"):
    ax.text(x, y, s, fontsize=size, color=color, ha=ha, va=va,
            fontweight=weight, fontstyle=style, linespacing=1.45)


# --- which cells are held out, per protocol ---------------------------------
# 1. window-pooled: every trial straddles the split (one window of each is tested)
held_win = {(s, t, (s + t) % N_WIN) for s in range(N_SUBJ) for t in range(N_TRIAL)}
# 2. trial-grouped, participants pooled: whole trials held out, every participant
#    still appears on both sides
held_trial = {(0, 2), (1, 0), (2, 1), (3, 2)}
# 3./4. subject-grouped: participant 4 is held out entirely
held_subj = {3}

PROTOCOLS = [
    ("1. Window-pooled $k$-fold",                  "yes", "yes", "0.711", "windows"),
    ("2. Trial-grouped,\nparticipants pooled",     "no",  "yes", "0.651", "trials"),
    ("3. Subject-grouped windows",                 "no",  "no",  "0.515", "subjects"),
    ("4. Leave-one-subject-out\n(trial level)",    "no",  "no",  "0.516", "aggregated"),
]

for row, (name, tr_ov, pt_ov, auc, mode) in enumerate(PROTOCOLS):
    y = ROW_Y[row]

    # protocol name + the two properties that define it
    txt(1.0, y + CELL_H / 2, name, size=7.5, weight="bold", va="center")
    txt(1.0, y - 3.2, f"trial overlap: {tr_ov}", size=6.8, color=GRAY)
    txt(1.0, y - 5.6, f"participant overlap: {pt_ov}", size=6.8, color=GRAY)

    for s in range(N_SUBJ):
        for t in range(N_TRIAL):
            if mode == "aggregated":
                # trial-level scoring: the four windows collapse into one unit
                c = TEST if s in held_subj else TRAIN
                x = cell_x(s, t, 0)
                ax.add_patch(Rectangle((x, y), TRIAL_W, CELL_H, facecolor=c,
                                       edgecolor="white", lw=0.7))
                continue
            for w in range(N_WIN):
                if mode == "windows":
                    test = (s, t, w) in held_win
                elif mode == "trials":
                    test = (s, t) in held_trial
                else:
                    test = s in held_subj
                ax.add_patch(Rectangle((cell_x(s, t, w), y), CELL_W, CELL_H,
                                       facecolor=TEST if test else TRAIN,
                                       edgecolor="white", lw=0.5))

    txt(AUC_X, y + CELL_H / 2, auc, size=10.0, weight="bold", ha="center")

# --- headers ----------------------------------------------------------------
top = ROW_Y[0] + CELL_H
for s in range(N_SUBJ):
    txt(cell_x(s, 0, 0) + SUBJ_W / 2, top + 3.0, f"P{s + 1}", size=7.5, color=GRAY, ha="center")
txt(X0 + (N_SUBJ * SUBJ_W + (N_SUBJ - 1) * SUBJ_GAP) / 2, top + 6.6,
    "participants", size=7.5, color=FAINT, ha="center", style="italic")
txt(AUC_X, top + 3.0, "AUC", size=7.5, color=GRAY, ha="center")
txt(AUC_X, top + 6.6, "DEAP valence", size=7.5, color=FAINT, ha="center", style="italic")

# --- arrows: one per adjacent pair, naming the single channel it removes -----
# Protocols 1-3 differ only in the grouping variable, so the first two arrows each isolate a
# single channel. Protocol 4 also switches to LOSO and fits a train-fold scaler, so its step is a
# robustness check, not an isolated channel: it is drawn in grey and names all three changes.
EFFECTS = [
    ("correlated-window effect", "−0.060", INK),
    ("participant-overlap effect", "−0.136", INK),
    ("aggregation, resampling\nand normalization", "+0.001", GRAY),
]
for i, (label, delta, colour) in enumerate(EFFECTS):
    y_top = ROW_Y[i] + CELL_H / 2 - 3.6
    y_bot = ROW_Y[i + 1] + CELL_H / 2 + 3.6
    ax.add_patch(FancyArrowPatch((ARROW_X, y_top), (ARROW_X, y_bot),
                                 arrowstyle="-|>", mutation_scale=11,
                                 lw=1.0, color=colour, shrinkA=0, shrinkB=0))
    mid = (y_top + y_bot) / 2
    offset = 1.6 if "\n" in label else 0.0
    txt(LABEL_X, mid + 1.8 + offset, label, size=7.4, color=colour)
    txt(LABEL_X, mid - 2.6 - offset, delta, size=8.6, color=colour, weight="bold")

# --- legend + reading note --------------------------------------------------
ax.add_patch(Rectangle((31.0, 12.0), 2.6, 3.4, facecolor=TRAIN, edgecolor="white", lw=0.5))
txt(34.6, 13.7, "training", size=7.4, color=GRAY)
ax.add_patch(Rectangle((46.0, 12.0), 2.6, 3.4, facecolor=TEST, edgecolor="white", lw=0.5))
txt(49.6, 13.7, "held out for testing", size=7.4, color=GRAY)
txt(31.0, 6.2, "Each cell is one overlapping window; three windows make a trial, three trials a participant. Rows 1 to 3\n"
               "differ only in the train/test assignment. Protocol 4 also aggregates each trial's windows, so there each\n"
               "cell is a whole trial. Chance is 0.500.",
    size=7.0, color=FAINT)

for ext in ("png", "pdf"):
    fig.savefig(f"fig1_protocol_decomposition.{ext}", dpi=300 if ext == "png" else None,
                bbox_inches="tight", pad_inches=0.02)
print("wrote fig1_protocol_decomposition.png / .pdf")
