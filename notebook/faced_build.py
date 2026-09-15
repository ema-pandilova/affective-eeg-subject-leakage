"""
Build the FACED feature cache with the same 66-feature pipeline used for DEAP and DREAMER.

Sources
  EEG      Processed_data.zip from the FACED Synapse project (syn50614194; Chen et al., 2023, Scientific Data
           10:740): the dataset authors' preprocessed EEG, one pickle per participant holding an array of
           28 clips x 32 electrodes x 7,500 samples (the last 30 s of each clip at 250 Hz), clips ordered by
           video index and electrodes in the order of Electrode_Location.xlsx.
  Ratings  the per-clip valence and arousal ratings (continuous, 0 to 7) and presentation times from the
           BIDS events files of the NEMAR mirror (nm000112), which read them from the authors'
           After_remarks.mat by video index. Checked before use: the item order used by the converter matches
           DataStructureOfBehaviouralData.xlsx; participant numbering matches Recording_info.csv on sampling
           rate and sex for all 123 participants; the highest-rated emotion is the targeted one for all 24
           non-neutral clips; negative, neutral and positive clips have non-overlapping mean valence.

Adaptations to FACED, fixed before any classification was run
  * channels Fp1, F3, F7, Fp2, F4, F8 (FACED has no AF3/AF4; Fp1/Fp2 are the nearest prefrontal sites);
  * the authors' preprocessing is kept; the only change is anti-aliased resampling from 250 to 128 Hz;
  * the 30 s trial gives 14 windows of 4 s in 2 s steps;
  * presentation block (clips shown in same-valence blocks of four) = presentation rank // 4.

    python faced_build.py [--workers 8]
Writes cache/FACED.npz (X, val, aro, subj, trial, stim, rank, block) and cache/FACED_meta.json.
"""
from __future__ import annotations
import argparse, csv, html, json, pickle, re, time, zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from scipy.signal import resample_poly

import run_protocols as R

DATA = (R.HERE / "../../data/faced").resolve()
EVENTS = DATA / "nemar_events"
CH_FACED = ["Fp1", "F3", "F7", "Fp2", "F4", "F8"]     # stands in for R.CH = AF3, F3, F7, AF4, F4, F8
FS_IN, FS, WIN_S, STEP_S = 250, 128, 4, 2


def xlsx_rows(path):
    z = zipfile.ZipFile(path)
    shared = [html.unescape("".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S)))
              for si in re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode("utf8"), re.S)]
    rows = []
    for row in re.findall(r"<row[^>]*>(.*?)</row>", z.read("xl/worksheets/sheet1.xml").decode("utf8"), re.S):
        cells = []
        for attrs, inner in re.findall(r"<c ([^>]*?)(?:/>|>(.*?)</c>)", row, re.S):
            v = re.search(r"<v>(.*?)</v>", inner or "")
            val = v.group(1) if v else ""
            if 't="s"' in attrs and val:
                val = shared[int(val)]
            cells.append(val.strip())
        rows.append(cells)
    return rows


def electrode_order():
    """Electrode order of the processed data. The authors note that after preprocessing the first cohort's electrodes
    were reordered to match the second cohort, so the second-cohort table (numbered 1 to 32) gives the order."""
    rows = xlsx_rows(DATA / "Electrode_Location.xlsx")
    start = next(i for i, r in enumerate(rows) if any("second cohort" in c for c in r))
    order = {}
    for r in rows[start + 1:]:
        if not any(r):
            break
        for c in range(0, 8, 2):
            if c + 1 < len(r) and r[c].isdigit():
                order[int(r[c])] = r[c + 1]
    assert sorted(order) == list(range(1, 33)), order
    return [order[i] for i in range(1, 33)]


def ratings(sub):
    ev = [e for e in csv.DictReader(open(EVENTS / f"sub-{sub:03d}_events.tsv", encoding="utf-8-sig"), delimiter="\t")
          if e["video_index"] not in ("", "n/a")]
    ev.sort(key=lambda e: float(e["onset"]))
    out = {}
    for rank, e in enumerate(ev):
        out[int(e["video_index"]) - 1] = dict(val=float(e["Valence"]), aro=float(e["Arousal"]), rank=rank)
    assert sorted(out) == list(range(28)), f"sub {sub}: clips {sorted(out)}"
    return out


def features_for(args):
    sub, arr, names = args
    idx = [names.index(c) for c in CH_FACED]
    rat = ratings(sub)
    X, val, aro, stim, rank = [], [], [], [], []
    for v in range(arr.shape[0]):
        seg = resample_poly(arr[v, idx, :].astype(np.float64), FS, FS_IN, axis=1)
        for st in range(0, seg.shape[1] - WIN_S * FS + 1, STEP_S * FS):
            X.append(list(R.window_features(seg[:, st:st + WIN_S * FS]).values()))
            val.append(rat[v]["val"]); aro.append(rat[v]["aro"]); stim.append(v); rank.append(rat[v]["rank"])
    return sub, np.array(X), np.array(val), np.array(aro), np.array(stim), np.array(rank)


def load_pickles(zpath):
    z = zipfile.ZipFile(zpath)
    members = sorted(m for m in z.namelist() if m.lower().endswith(".pkl"))
    for m in members:
        sub = int(re.findall(r"(\d{3})", Path(m).stem)[-1])
        with z.open(m) as fh:
            arr = pickle.load(fh)
        yield sub, m, np.asarray(arr)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    t0 = time.time()
    names = electrode_order()
    assert len(names) == 32 and all(c in names for c in CH_FACED), names
    rec = {int(r["sub"].strip()[3:]): r for r in csv.DictReader(open(DATA / "Recording_info.csv", encoding="utf-8-sig"))}
    arrays, amp, members = {}, {}, {}
    for sub, m, arr in load_pickles(DATA / "Processed_data.zip"):
        assert arr.shape == (28, 32, 7500), (m, arr.shape)
        arrays[sub] = arr.astype(np.float32); members[sub] = m
        amp[sub] = float(np.median(np.std(arr[:, [names.index(c) for c in CH_FACED], :], axis=2)))
    subs = sorted(arrays)
    print(f"{len(subs)} participants loaded [{time.time()-t0:.0f}s]", flush=True)
    # unit check: the frontal-channel SD should sit on one scale for every participant (a V/uV mix would differ ~1e6)
    by_unit = {}
    for s in subs:
        by_unit.setdefault(rec[s]["Unit"].strip(), []).append(amp[s])
    unit_summary = {u: dict(n=len(v), median_sd=float(np.median(v)), min_sd=float(np.min(v)), max_sd=float(np.max(v)))
                    for u, v in by_unit.items()}
    print("median frontal SD by raw unit:", unit_summary, flush=True)
    ratio = max(u["median_sd"] for u in unit_summary.values()) / min(u["median_sd"] for u in unit_summary.values())
    assert ratio < 100, f"processed data appear to mix units (ratio {ratio:.1f}); stop and convert before building features"

    results = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for sub, X, val, aro, stim, rank in ex.map(features_for, [(s, arrays[s], names) for s in subs], chunksize=2):
            results[sub] = (X, val, aro, stim, rank)
            if len(results) % 20 == 0:
                print(f"  features for {len(results)} participants [{time.time()-t0:.0f}s]", flush=True)
    X = np.concatenate([results[s][0] for s in subs])
    val = np.concatenate([results[s][1] for s in subs]); aro = np.concatenate([results[s][2] for s in subs])
    stim = np.concatenate([results[s][3] for s in subs]); rank = np.concatenate([results[s][4] for s in subs])
    subj = np.concatenate([[s] * len(results[s][1]) for s in subs])
    trial = np.array([f"{s}_{v}" for s, v in zip(subj, stim)])
    R.CACHE.mkdir(exist_ok=True)
    np.savez_compressed(R.CACHE / "FACED.npz", X=X, val=val, aro=aro, subj=subj, trial=trial, stim=stim,
                        rank=rank, block=rank // 4)
    meta = dict(eeg_source="FACED Synapse syn50614194, Processed_data.zip (authors' preprocessing)",
                ratings_source="NEMAR nm000112 BIDS events (from After_remarks.mat), checked as described in faced_build.py",
                participants=len(subs), trials=int(len(np.unique(trial))), windows=int(len(val)),
                windows_per_trial=sorted(set(np.unique(trial, return_counts=True)[1].tolist())),
                channels=CH_FACED, electrode_order=names, fs=FS, unit_check=unit_summary,
                cohorts={str(k): int(v) for k, v in zip(*np.unique([rec[s]["Cohort "].strip() for s in subs], return_counts=True))},
                zip_members=members, runtime_s=round(time.time() - t0, 1))
    (R.CACHE / "FACED_meta.json").write_text(json.dumps(meta, indent=1))
    print({k: v for k, v in meta.items() if k not in ("zip_members", "electrode_order")}, flush=True)
