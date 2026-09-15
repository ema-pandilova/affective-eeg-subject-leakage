"""Turn two finished screening sheets into the coding sheets, following protocol section 5.

Run this after both coders have screened independently and the adjudicator has settled every
disagreement and every 'unsure'. It walks the frozen order from the top, takes studies both coders
(or the adjudicator) marked eligible, stops at the target, records the position where the target was
reached, and writes a blank coding sheet per coder. It also fills in the PRISMA screening counts.

  python make_coding_sheets.py coderA_screening.csv coderB_screening.csv [--adjudication adjudication.csv]
                               [--target 45]

Disagreements and 'unsure' answers must be resolved in the adjudication file before the sample can be
fixed; the script lists them and stops if any remain unresolved within the stretch it needs to read.
It decides no eligibility itself.
"""
from __future__ import annotations
import argparse, csv, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE_COLS = ["X1", "H1", "H2", "H3", "H4", "S1", "S2", "S3", "S4", "U1", "S5", "N1", "T1", "M1",
             "R1", "R2", "R3", "R4", "C1", "Q_split", "Q_norm", "Q_claim", "note", "minutes"]
OUT_COLS = ["pid", "screen_position", "doi", "year", "title", "url",
            "coder_name", "date_coded", "version_coded"] + CODE_COLS


def read(path):
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8-sig")))
    if not rows:
        sys.exit(f"{path}: empty")
    names = {r.get("coder_name", "").strip() for r in rows if r.get("coder_name", "").strip()}
    return {r["screen_position"]: r for r in rows}, ("|".join(sorted(names)) if names else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_a"); ap.add_argument("sheet_b")
    ap.add_argument("--adjudication", default="")
    ap.add_argument("--target", type=int, default=45)
    a = ap.parse_args()

    A, na = read(a.sheet_a)
    B, nb = read(a.sheet_b)
    if na and nb and na.strip().lower() == nb.strip().lower():
        sys.exit(f"REFUSED: both screening sheets name the same coder ({na})")

    adj = {}
    if a.adjudication and Path(a.adjudication).exists():
        adj = {r["screen_position"]: r["E1_adjudicated"].strip()
               for r in csv.DictReader(open(a.adjudication, newline="", encoding="utf-8-sig"))
               if r.get("E1_adjudicated", "").strip()}

    # Walk the frozen order once. Every unresolved record that falls above the point where the target
    # is reached could change the sample, so all of them are collected and reported together: the
    # adjudicator settles them in one pass rather than being fed one at a time.
    order = sorted(set(A) & set(B), key=lambda p: int(p))
    included, unresolved, screened, excluded = [], [], 0, 0
    for pos in order:
        ea, eb = A[pos].get("E1", "").strip(), B[pos].get("E1", "").strip()
        screened += 1
        verdict = adj.get(pos)
        if verdict is None:
            if not ea or not eb:
                unresolved.append((pos, "not screened by both", ea, eb)); continue
            if ea == eb and ea in ("eligible", "not_eligible"):
                verdict = ea
            else:
                unresolved.append((pos, "disagreement or unsure", ea, eb)); continue
        if verdict == "eligible":
            included.append(A[pos])
            if len(included) >= a.target and not unresolved:
                break
            if len(included) >= a.target:
                break
        else:
            excluded += 1

    if unresolved:
        print(f"Cannot fix the sample yet: {len(unresolved)} record(s) need the adjudicator.\n")
        for pos, why, ea, eb in unresolved:
            print(f"  position {pos}: {why} (A='{ea}' B='{eb}')")
        print(f"\nAdd one row per position to the adjudication file with screen_position and")
        print("E1_adjudicated (eligible / not_eligible), then rerun. Every one of these sits above the")
        print("point where the target is reached, so each could change which studies are coded.")
        sys.exit(1)

    if len(included) < a.target:
        print(f"Only {len(included)} eligible studies in the {screened} records screened; "
              f"target is {a.target}. Screen further down the order and rerun.")
        sys.exit(1)

    for i, r in enumerate(included, 1):
        r["pid"] = f"B{i:03d}"

    for c in ("A", "B"):
        path = HERE / f"coder{c}_coding.csv"
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=OUT_COLS, extrasaction="ignore")
            w.writeheader()
            w.writerows({**r, "coder_name": "", "date_coded": "", "version_coded": "1.1",
                         **{k: "" for k in CODE_COLS}} for r in included)
        print(f"wrote {path.name}: {len(included)} studies, coding columns blank")

    # Bench work package for the same 45 studies, so the coding page offered by protocol section 6
    # shows the Part B sample rather than the Part A set it shipped with. Coder names ship blank.
    import json
    cb = list(csv.DictReader(open(HERE.parent / "coding_rubric_v1.1.csv", newline="", encoding="utf-8-sig")))
    pkg = dict(kind="work-package", exportedAt=f"{__import__('datetime').date.today().isoformat()}T00:00:00.000Z",
               cfg=dict(names={"A": "", "B": "", "adj": "", "coord": ""}, target=a.target,
                        seed=20260914, codebook="1.1", mode="B"),
               sample=None, codebook=cb,
               papers=[dict(pid=r["pid"], title=r.get("title", ""), authors="", year=r.get("year", ""),
                            venue=r.get("venue", ""), doi=r.get("doi", ""), url=r.get("url", ""),
                            rank=i, source="partB") for i, r in enumerate(included, 1)])
    (HERE / "bench-work-package-partB.json").write_text(json.dumps(pkg, indent=1))
    print(f"wrote bench-work-package-partB.json: {len(included)} papers, coder names blank")

    stop = int(included[-1]["screen_position"])
    prisma = [
        ("Records identified (OpenAlex, 8 dataset terms x 2 search fields)", ""),
        ("Records after de-duplication (screening frame)", ""),
        ("Records screened to reach the target", screened),
        ("Records excluded at screening", excluded),
        ("Studies included and coded", len(included)),
        ("Position in the frozen order at which the target was reached", stop),
    ]
    with open(HERE / "prisma_screening_counts.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["stage", "n"]); w.writerows(prisma)
    print(f"\nscreened {screened} records to reach {len(included)} eligible; stopped at position {stop}")
    print("wrote prisma_screening_counts.csv")


if __name__ == "__main__":
    main()
