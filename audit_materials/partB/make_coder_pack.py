"""Build the two coders' screening packs from the frozen screening order.

Produces one sheet per coder with identical rows in the protocol's fixed order and every judgement
column blank, plus the calibration set required by protocol section 6. Column names match the rubric's
screen-stage fields (E1, E2, note) so compute_agreement.py reads the sheets without translation.

Calibration papers are taken from the tail of the frozen order, which cannot collide with the sample:
the sample is drawn from the head, screening in order until the target is reached.
"""
import csv, shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
N_CALIB = 3
COL = ["screen_position", "doi", "title", "year", "venue", "type", "language", "url",
       "coder_name", "date_screened", "E1", "E2", "note"]

rows = list(csv.DictReader(open(HERE / "screening_order.csv", encoding="utf-8-sig")))
for r in rows:                                    # rename to the rubric's field names
    r["E1"] = r.pop("E1_eligible", "")
    r["E2"] = r.pop("E2_exclusion_reason", "")
    r["note"] = r.pop("screen_note", "")

calib, sample = rows[-N_CALIB:], rows[:-N_CALIB]


def write(path, recs):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COL, extrasaction="ignore")
        w.writeheader()
        w.writerows({**r, "coder_name": "", "date_screened": "", "E1": "", "E2": "", "note": ""} for r in recs)


write(HERE / "screening_order.csv", rows)                       # canonical order, corrected columns
for c in ("A", "B"):
    write(HERE / f"coder{c}_screening.csv", sample)
    write(HERE / f"coder{c}_calibration.csv", calib)

print(f"screening frame: {len(rows)} records")
print(f"  coderA_screening.csv / coderB_screening.csv : {len(sample)} rows each, blank")
print(f"  coderA_calibration.csv / coderB_calibration.csv : {len(calib)} rows each, blank")
print("\ncalibration papers (tail of the frozen order, cannot collide with the sample):")
for r in calib:
    print(f"  #{r['screen_position']}  {r['title'][:78]}")
