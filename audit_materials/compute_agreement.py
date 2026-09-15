"""Inter-rater agreement for the double-coded audit, from the Audit Coding Bench exports.

The page (frontiers_revision/audit_bench/audit-coding-bench.html) shows point estimates only.
This script produces the numbers the manuscript reports: percent agreement, Cohen's kappa,
Gwet's AC1 and PABAK, each with a 95% percentile bootstrap CI that resamples PAPERS, plus a
sensitivity analysis that drops papers where either coder answered "unclear".

Usage:
  python irr_from_bench.py audit-codebook-v1.1.csv audit-code-coderA-<date>.csv audit-code-coderB-<date>.csv
        [--boot 2000] [--seed 20260914] [--out agreement.csv]

Inputs are the three CSVs exported from the page's Export tab, after both coders have locked.
The script refuses to run if the two sheets carry the same coder name, if a coder name looks
like a language model, or if the two sheets are identical on every coded field, because none of
those is a second independent rater.

Categories follow the pair actually observed (the same rule the page uses), so its preview table
and this script agree; the CIs and PABAK are added here. Numeric fields are compared within
0.005 after percentages are converted to proportions, and blank-versus-blank counts as a match.
Fields are compared only on papers where both coders reached the question, that is where the
answers to the questions it depends on (shown_when in the codebook) are satisfied for both.
"""
import argparse
import csv
import sys

import numpy as np

LLM_MARKERS = ("llm", "gpt", "claude", "gemini", "chatgpt", "copilot", "bard", "assistant")


def num_norm(x):
    try:
        v = float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return v / 100 if 1 < v <= 100 else v


def same_num(a, b):
    if not str(a).strip() and not str(b).strip():
        return True
    x, y = num_norm(a), num_norm(b)
    if x is None or y is None:
        return str(a).strip().lower() == str(b).strip().lower()
    return abs(x - y) <= 0.005


def stats(a, b, cats):
    n = len(a)
    if n == 0:
        return {}
    po = float(np.mean([x == y for x, y in zip(a, b)]))
    if len(cats) < 2:
        return {"Po": po, "kappa": np.nan, "AC1": np.nan, "PABAK": np.nan}
    pa = {c: a.count(c) / n for c in cats}
    pb = {c: b.count(c) / n for c in cats}
    pe = sum(pa[c] * pb[c] for c in cats)
    kappa = np.nan if pe >= 1 else (po - pe) / (1 - pe)
    k = len(cats)
    pi = [(pa[c] + pb[c]) / 2 for c in cats]
    peg = sum(p * (1 - p) for p in pi) / (k - 1)
    ac1 = np.nan if peg >= 1 else (po - peg) / (1 - peg)
    return {"Po": po, "kappa": kappa, "AC1": ac1, "PABAK": (k * po - 1) / (k - 1)}


def boot_ci(a, b, boot, rng):
    n = len(a)
    out = {k: [] for k in ("Po", "kappa", "AC1", "PABAK")}
    for _ in range(boot):
        idx = rng.integers(0, n, n)
        xa = [a[i] for i in idx]
        xb = [b[i] for i in idx]
        s = stats(xa, xb, sorted(set(xa) | set(xb)))
        for k in out:
            out[k].append(s.get(k, np.nan))
    with np.errstate(all="ignore"):
        return {k: (np.nanpercentile(v, 2.5), np.nanpercentile(v, 97.5)) if np.any(np.isfinite(v)) else (np.nan, np.nan)
                for k, v in out.items()}


def read_sheet(path):
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8-sig")))
    if not rows:
        sys.exit(f"{path}: empty sheet")
    names = {r.get("coder_name", "").strip() for r in rows if r.get("coder_name", "").strip()}
    return {r["pid"]: r for r in rows}, (names.pop() if len(names) == 1 else "|".join(sorted(names)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("codebook")
    ap.add_argument("sheet_a")
    ap.add_argument("sheet_b")
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20260914)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    cb = [r for r in csv.DictReader(open(args.codebook, newline="", encoding="utf-8-sig"))
          if r["stage"] == "code" and r["type"] in ("cat", "num")]
    if not cb:
        cb = [r for r in csv.DictReader(open(args.codebook, newline="", encoding="utf-8-sig")) if r["type"] in ("cat", "num")]
    A, name_a = read_sheet(args.sheet_a)
    B, name_b = read_sheet(args.sheet_b)

    if name_a.strip().lower() == name_b.strip().lower():
        sys.exit(f"REFUSED: both sheets name the same coder ({name_a}); the two sheets must come from different people")
    for nm in (name_a, name_b):
        if any(m in nm.lower() for m in LLM_MARKERS):
            sys.exit(f"REFUSED: coder name '{nm}' looks like a language model; an AI system is not an independent reviewer")

    common = sorted(set(A) & set(B))
    print(f"coders: {name_a} vs {name_b}")
    print(f"papers coded by both: {len(common)} (A only {len(set(A) - set(B))}, B only {len(set(B) - set(A))})")
    coded_fields = [r["field"] for r in cb]
    if common and all(all(A[p].get(f, "") == B[p].get(f, "") for f in coded_fields) for p in common):
        sys.exit("REFUSED: the two sheets are identical on every coded field; check that the coding was independent")

    def cond_ok(row, when):
        return all(row.get(k, "") == v for k, v in when)

    rng = np.random.default_rng(args.seed)
    out_rows = []
    for r in cb:
        field, typ = r["field"], r["type"]
        when = [kv.split("=", 1) for kv in r["shown_when"].split(" & ") if kv]
        a, b, one_sided, skipped = [], [], 0, 0
        for p in common:
            ra, rb = A[p], B[p]
            ma, mb = cond_ok(ra, when), cond_ok(rb, when)
            if ma != mb:
                one_sided += 1
                continue
            if not ma:
                skipped += 1
                continue
            xa, xb = ra.get(field, "").strip(), rb.get(field, "").strip()
            if typ == "num":
                a.append(xa)
                b.append(xb)
                continue
            if not xa or not xb:
                one_sided += 1
                continue
            a.append(xa)
            b.append(xb)
        if typ == "num":
            ok = [same_num(x, y) for x, y in zip(a, b)]
            out_rows.append([field, r["primary"], len(ok), "", f"{np.mean(ok):.3f}" if ok else "", "", "", "", one_sided, skipped,
                             "exact match within 0.005"])
            continue
        cats = sorted(set(a) | set(b))
        if len(cats) < 2:
            out_rows.append([field, r["primary"], len(a), len(cats), f"{np.mean([x == y for x, y in zip(a, b)]):.3f}" if a else "",
                             "", "", "", one_sided, skipped, "single category used by both coders; kappa undefined"])
            continue
        s = stats(a, b, cats)
        ci = boot_ci(a, b, args.boot, rng)
        keep = [i for i in range(len(a)) if a[i] != "unclear" and b[i] != "unclear"]
        sens = stats([a[i] for i in keep], [b[i] for i in keep],
                     sorted(set(a[i] for i in keep) | set(b[i] for i in keep))) if len(keep) > 1 else {}
        fmt = lambda k: f"{s[k]:.3f} [{ci[k][0]:.3f}, {ci[k][1]:.3f}]"
        marg = "A: " + "; ".join(f"{c}={a.count(c)}" for c in cats) + " | B: " + "; ".join(f"{c}={b.count(c)}" for c in cats)
        note = f"without unclear n={len(keep)} kappa={sens.get('kappa', float('nan')):.3f} AC1={sens.get('AC1', float('nan')):.3f} || {marg}" if sens else marg
        out_rows.append([field, r["primary"], len(a), len(cats), fmt("Po"), fmt("kappa"), fmt("AC1"), fmt("PABAK"),
                         one_sided, skipped, note])

    header = ["field", "primary", "n_papers", "categories_used", "percent_agreement [95% CI]", "cohen_kappa [95% CI]",
              "gwet_ac1 [95% CI]", "pabak [95% CI]", "one_sided", "not_applicable", "notes"]
    w = csv.writer(open(args.out, "w", newline="") if args.out else sys.stdout)
    w.writerow(header)
    w.writerows(out_rows)
    prim = [row for row in out_rows if row[1] == "yes" and row[5]]
    if prim and not args.out:
        ks = [float(row[5].split(" ")[0]) for row in prim]
        print(f"\nprimary fields: {len(prim)}, median kappa {np.median(ks):.3f}, min {min(ks):.3f}", file=sys.stderr)


if __name__ == "__main__":
    main()
