"""Part B systematic search: identification and de-duplication, then a seeded random screening order.

Executes the protocol's eligibility-independent steps only. Every judgement about whether a record is
eligible is left to the two human coders; this script decides nothing about any study.

Databases actually queried are recorded in search_log.csv with the exact strings, the date and the
counts returned. The search is run against OpenAlex, which is open and callable without credentials,
so the whole identification step is reproducible by anyone from this script alone. Scopus and Web of
Science, named in version 1.0 of the protocol, need institutional credentials and were not run; the
change is recorded in the protocol's change log.

Scope. The queries match a dataset name in the title or abstract, so the frame contains studies that
name DEAP, DREAMER or a SEED-family dataset where a search can see it. Studies that use one of these
datasets without naming it in the title or abstract are not reachable by any dataset-name query and
are outside the frame. This bounds what the sample can describe and is stated as a limitation, not
offered as a result.

Outputs (all written next to this script):
  search_log.csv          one row per query actually run
  records_raw.csv         every record retrieved, before de-duplication
  records_deduped.csv     after DOI then title+first-author de-duplication
  screening_order.csv     the de-duplicated set in the protocol's seeded random order, with blank
                          screening columns for each coder. Written BEFORE any screening starts.
  prisma_counts.csv       stage counts for the PRISMA diagram
"""
from __future__ import annotations
import csv, json, re, sys, time, urllib.parse, urllib.request
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SEED = 20260914                      # fixed by the protocol, section 5
MAILTO = "openalex-audit@example.org"
YEARS = (2011, 2025)   # floor is 2011, not 2012: OpenAlex dates the DEAP origin paper to its 2011
                       # online publication, and the protocol names the dataset-origin papers eligible.
                       # Coders apply the 2012-2025 rule to the publication year of record.
DATASET_TERMS = ['deap', 'dreamer', '"seed dataset"', '"seed database"',
                 '"sjtu emotion eeg dataset"', '"seed-iv"', '"seed-v"', '"seed-vii"']
CONCEPT = '(eeg OR electroencephalography) AND (emotion OR valence OR arousal OR affective)'


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read())
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


# Retrieval is deliberately wider than the eligibility rules. Conference papers are included because
# the protocol admits proceedings papers; preprints and non-English records are retrieved and then
# excluded by the coders at screening, so every exclusion is counted in the PRISMA flow rather than
# being hidden inside the query. Records with no indexed abstract are reachable through the title-only
# pass, which matters because several heavily cited studies have no abstract in OpenAlex.
TYPES = "article|review|preprint|book-chapter|conference-paper|proceedings-article|report"
SEARCH_FIELDS = ["title_and_abstract.search", "title.search"]


def openalex(term):
    q = f'{CONCEPT} AND {term}'
    recs, total = [], 0
    for field in SEARCH_FIELDS:
        filt = ",".join([f"{field}:{q}", f"publication_year:{YEARS[0]}-{YEARS[1]}", f"type:{TYPES}"])
        cursor, sub = "*", None
        while True:
            url = (f"https://api.openalex.org/works?filter={urllib.parse.quote(filt, safe=':,|')}"
                   f"&per-page=200&cursor={cursor}&mailto={MAILTO}")
            d = get(url)
            sub = d["meta"]["count"] if sub is None else sub
            for w in d["results"]:
                prim = (w.get("primary_location") or {})
                recs.append(dict(
                    source_db="OpenAlex", query=q, search_field=field,
                    doi=(w.get("doi") or "").replace("https://doi.org/", "").lower(),
                    title=(w.get("display_name") or "").strip(),
                    year=w.get("publication_year") or "",
                    venue=((prim.get("source") or {}).get("display_name") or ""),
                    type=w.get("type") or "",
                    language=w.get("language") or "",
                    first_author=next((a["author"]["display_name"] for a in (w.get("authorships") or [])
                                       if a.get("author")), ""),
                    cited_by=w.get("cited_by_count", 0),
                    is_oa=(w.get("open_access") or {}).get("is_oa", False),
                    url=(w.get("best_oa_location") or {}).get("landing_page_url") or
                        (f"https://doi.org/{(w.get('doi') or '').replace('https://doi.org/','')}" if w.get("doi") else ""),
                    openalex_id=w.get("id", "")))
            cursor = d["meta"].get("next_cursor")
            if not cursor or not d["results"]:
                break
            time.sleep(0.2)
        total += sub
    return q, total, recs


def norm_title(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())[:90]


def main():
    log, raw = [], []
    for term in DATASET_TERMS:
        q, total, recs = openalex(term)
        log.append(dict(date_run=date.today().isoformat(), database="OpenAlex", query=q,
                        limits=f"{YEARS[0]}-{YEARS[1]}; English; type article/review/preprint",
                        n_returned=total, n_retrieved=len(recs)))
        raw += recs
        print(f"  {term:32s} {total:6d} returned, {len(recs):6d} retrieved", flush=True)

    # de-duplicate: DOI first, then normalised title + first author surname
    seen, dedup, dup_doi, dup_title = set(), [], 0, 0
    for r in sorted(raw, key=lambda r: (not r["doi"], -r["cited_by"])):
        if r["doi"]:
            k = ("doi", r["doi"])
            if k in seen:
                dup_doi += 1
                continue
        else:
            k = ("ti", norm_title(r["title"]), (r["first_author"].split()[-1].lower() if r["first_author"] else ""))
            if k in seen:
                dup_title += 1
                continue
        seen.add(k)
        dedup.append(r)

    # seeded random screening order, fixed before screening begins
    order = np.random.default_rng(SEED).permutation(len(dedup))
    ordered = [dedup[i] for i in order]
    for i, r in enumerate(ordered, 1):
        r["screen_position"] = i

    def write(name, rows, fields):
        with open(HERE / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader(); w.writerows(rows)

    rec_fields = ["screen_position", "doi", "title", "year", "venue", "type", "language", "first_author",
                  "cited_by", "is_oa", "url", "source_db", "search_field", "openalex_id", "query"]
    write("search_log.csv", log, list(log[0].keys()))
    write("records_raw.csv", raw, [f for f in rec_fields if f != "screen_position"])
    write("records_deduped.csv", ordered, rec_fields)

    screen_fields = ["screen_position", "doi", "title", "year", "venue", "type", "language", "url",
                     "coder_name", "date_screened", "E1_eligible", "E2_exclusion_reason", "screen_note"]
    write("screening_order.csv", [{**r, "coder_name": "", "date_screened": "",
                                   "E1_eligible": "", "E2_exclusion_reason": "", "screen_note": ""}
                                  for r in ordered], screen_fields)

    prisma = [
        dict(stage="Records identified (OpenAlex, 8 dataset terms x 2 search fields)", n=len(raw)),
        dict(stage="Duplicates removed by DOI", n=dup_doi),
        dict(stage="Duplicates removed by title and first author", n=dup_title),
        dict(stage="Records after de-duplication (screening frame)", n=len(dedup)),
        dict(stage="Records screened (title and abstract)", n=""),
        dict(stage="Records excluded at screening", n=""),
        dict(stage="Full texts assessed", n=""),
        dict(stage="Full texts excluded, with reasons", n=""),
        dict(stage="Studies included and coded (protocol target 45)", n=""),
    ]
    write("prisma_counts.csv", prisma, ["stage", "n"])

    print(f"\nretrieved {len(raw)}; removed {dup_doi} DOI duplicates and {dup_title} title duplicates")
    print(f"screening frame: {len(dedup)} records, ordered with seed {SEED}")
    print("wrote search_log.csv, records_raw.csv, records_deduped.csv, screening_order.csv, prisma_counts.csv")


if __name__ == "__main__":
    main()
