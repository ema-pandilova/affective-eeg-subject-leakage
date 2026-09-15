"""
Frontiers revision (rev1), Figure 2: evaluation designs only, no outcomes.

(a) The four protocols on a toy dataset (4 participants, 3 trials, 3 windows per trial). Consecutive rows
    change which unit is kept together; the notes say what changes, not what effect is "isolated".
(b) The size-matched participant-block x stimulus-block design for one test cell, for the seen-stimulus
    and unseen-stimulus arms.

    python rev1_fig_design.py   -> results/rev1/figures/fig_design.{pdf,png}
"""
from pathlib import Path
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

mpl.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.0, "pdf.fonttype": 42})
TRAIN, TEST, DROP = "#2a78d6", "#eb6834", "#dcdbd6"
INK, GRAY, FAINT = "#0b0b0b", "#52514e", "#8a8984"
OUT = (Path(__file__).resolve().parent / "../results/rev1/figures").resolve()
OUT.mkdir(parents=True, exist_ok=True)

fig = plt.figure(figsize=(7.2, 7.4))
ax = fig.add_axes([0, 0.34, 1, 0.66]); ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
bx = fig.add_axes([0, 0, 1, 0.33]); bx.set_xlim(0, 100); bx.set_ylim(0, 100); bx.axis("off")


def txt(a, x, y, s, size=8.0, color=INK, ha="left", va="center", weight="normal", style="normal"):
    a.text(x, y, s, fontsize=size, color=color, ha=ha, va=va, fontweight=weight, fontstyle=style, linespacing=1.4)


# ------------------------------------------------------------------ (a) protocols
N_S, N_T, N_W = 4, 3, 3
X0, CW, WG, TG, SG, CH = 30.0, 0.78, 0.06, 0.55, 1.4, 5.0
TW = N_W * CW + (N_W - 1) * WG
SW = N_T * TW + (N_T - 1) * TG
ROWS = [80.0, 60.0, 40.0, 20.0]
ARROW_X, NOTE_X = 71.0, 73.5


def cx(s, t, w):
    return X0 + s * (SW + SG) + t * (TW + TG) + w * (CW + WG)


held_win = {(s, t, (s + t) % N_W) for s in range(N_S) for t in range(N_T)}
held_trial = {(0, 2), (1, 0), (2, 1), (3, 2)}
PROT = [("P1  Window-pooled 5-fold", "trials split across folds", "participants on both sides", "windows"),
        ("P2  Trial-grouped 5-fold", "trials kept whole", "participants on both sides", "trials"),
        ("P3  Participant-grouped 5-fold", "trials kept whole", "participants held out", "subjects"),
        ("P4  Leave-one-participant-out", "trials kept whole", "one participant held out", "loso")]
txt(ax, 1.0, 97.5, "a", size=10, weight="bold")
for r, (name, l1, l2, mode) in enumerate(PROT):
    y = ROWS[r]
    txt(ax, 1.0, y + CH / 2 + 0.6, name, size=7.8, weight="bold")
    txt(ax, 1.0, y - 2.8, l1, size=6.9, color=GRAY)
    txt(ax, 1.0, y - 5.6, l2, size=6.9, color=GRAY)
    for s in range(N_S):
        for t in range(N_T):
            for w in range(N_W):
                if mode == "windows":
                    test = (s, t, w) in held_win
                elif mode == "trials":
                    test = (s, t) in held_trial
                elif mode == "subjects":
                    test = s == 3
                else:
                    test = s == 3
                ax.add_patch(Rectangle((cx(s, t, w), y), CW, CH, facecolor=TEST if test else TRAIN, edgecolor="white", lw=0.6))
top = ROWS[0] + CH
for s in range(N_S):
    txt(ax, cx(s, 0, 0) + SW / 2, top + 3.2, f"participant {s + 1}", size=7.0, color=GRAY, ha="center")
NOTES = ["windows of a trial kept together", "participants kept apart", "one participant per fold\n(more training data per fold)"]
for i, note in enumerate(NOTES):
    yt, yb = ROWS[i] + CH / 2 - 4.0, ROWS[i + 1] + CH / 2 + 4.0
    ax.add_patch(FancyArrowPatch((ARROW_X, yt), (ARROW_X, yb), arrowstyle="-|>", mutation_scale=10, lw=0.9, color=GRAY))
    txt(ax, NOTE_X, (yt + yb) / 2, note, size=7.0, color=GRAY)
ax.add_patch(Rectangle((30.0, 4.0), 2.4, 3.2, facecolor=TRAIN, edgecolor="white")); txt(ax, 33.2, 5.6, "training", size=7.0, color=GRAY)
ax.add_patch(Rectangle((44.0, 4.0), 2.4, 3.2, facecolor=TEST, edgecolor="white")); txt(ax, 47.2, 5.6, "held out for testing", size=7.0, color=GRAY)
ax.add_patch(Rectangle((66.0, 4.0), 2.4, 3.2, facecolor=DROP, edgecolor="white")); txt(ax, 69.2, 5.6, "not used (panel b)", size=7.0, color=GRAY)
txt(ax, 1.0, 5.6, "Each cell is one window; three windows\nform a trial, three trials a participant.", size=6.6, color=FAINT)

# ------------------------------------------------------------------ (b) participant x stimulus design
txt(bx, 1.0, 95, "b", size=10, weight="bold")
KS, KV = 5, 4                      # illustrative block counts (DEAP uses 8 x 5, DREAMER 6 x 6)
I, J = 1, 1                        # test cell
GW, GH = 4.2, 12.0


def grid(x0, title, drop_col):
    txt(bx, x0 + KV * GW / 2, 86, title, size=7.8, weight="bold", ha="center")
    for r in range(KS):
        for c in range(KV):
            if r == I and c == J:
                col = TEST
            elif r == I or c == drop_col:
                col = DROP
            else:
                col = TRAIN
            bx.add_patch(Rectangle((x0 + c * GW, 72 - (r + 1) * GH), GW, GH, facecolor=col, edgecolor="white", lw=0.9))
    txt(bx, x0 + KV * GW / 2, 76, "stimulus blocks", size=6.8, color=GRAY, ha="center")
    txt(bx, x0 - 1.2, 72 - KS * GH / 2, "participant\nblocks", size=6.8, color=GRAY, ha="right")


grid(16.0, "Unseen participant, seen stimulus", drop_col=(J + 1) % KV)
grid(56.0, "Unseen participant, unseen stimulus", drop_col=J)
txt(bx, 1.0, 5.5, "Both arms test the same cell, train on the same participants and on the same number of trials and stimuli, "
                  "and differ only\nin which stimulus block is left out: another block (left) or the test block itself (right). "
                  "Every cell is tested once per arm.", size=6.8, color=FAINT)

for ext in ("pdf", "png"):
    fig.savefig(OUT / f"fig_design.{ext}", dpi=300 if ext == "png" else None, bbox_inches="tight", pad_inches=0.03)
print("wrote", OUT / "fig_design.pdf")
