# Data

Datasets are **not committed** to this repository. Only this README and the
`.gitkeep` placeholders are tracked; everything else in `raw/` and `processed/` is
git-ignored.

## Primary dataset — UCI Student Performance

| | |
| --- | --- |
| Source | UCI Machine Learning Repository, dataset ID 320 — <https://archive.ics.uci.edu/dataset/320/student+performance> |
| Archive | <https://archive.ics.uci.edu/static/public/320/student+performance.zip> |
| Licence | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (separate from this repository's MIT software licence) |
| Creator | Paulo Cortez, University of Minho |
| Citation | Cortez, P., & Silva, A. M. G. (2008). *Using Data Mining to Predict Secondary School Student Performance.* In A. Brito & J. Teixeira (Eds.), Proceedings of the 5th Future Business Technology Conference (FUBUTEC 2008), pp. 5–12. Porto, Portugal: EUROSIS. |

Two cohorts of students in two Portuguese secondary schools (Gabriel Pereira and
Mousinho da Silveira):

| Cohort key   | File              | Subject             | Rows | Columns |
| ------------ | ----------------- | ------------------- | ---- | ------- |
| `math`       | `student-mat.csv` | Mathematics         | 395  | 33      |
| `portuguese` | `student-por.csv` | Portuguese language | 649  | 33      |

Pinned SHA-256 checksums (also in `backend/analytics/data/cohorts.py`):

```
e47f9ee225e1ee6e69b7564e6dac7123e80b8486677fe111f351964cef5dec80  student-mat.csv
a7594a11d7771c0efe1a740824e0e833da9c4cad07c39a9766a874575563fb3f  student-por.csv
```
 Files are `;`-separated,
with text values quoted. Some numbers are also quoted (for example `G1`/`G2` in
`student-mat.csv`); the loader handles this.

All 33 attributes are documented in [`../docs/DATA_DICTIONARY.md`](../docs/DATA_DICTIONARY.md).

## Obtaining the data

From `backend/`, with the virtual environment active:

```bash
python -m analytics.data.download            # download if missing, then verify
python -m analytics.data.download --verify   # check existing files only
python -m analytics.data.download --force    # re-download
```

The script:

1. Downloads the official archive from UCI. The archive is nested: it contains
   `student.zip`, which contains the CSVs, UCI's `student.txt` attribute notes and
   `student-merge.R`.
2. Extracts `student-mat.csv`, `student-por.csv` and `student.txt` in memory. No
   archive is written to disk.
3. Verifies each CSV against its pinned SHA-256. On a mismatch it writes nothing and
   stops, because the upstream file has changed and should be reviewed before use.
4. Does nothing when verified files are already present.

The API never downloads data itself. If the files are missing, data endpoints return
`503 dataset_unavailable` with the command above.

## Layout

```
data/
├── raw/         # Official files exactly as published (git-ignored)
│   ├── student-mat.csv
│   ├── student-por.csv
│   └── student.txt      # UCI attribute notes, kept for provenance
└── processed/   # Outputs of the preprocessing pipeline, Phase 5 (git-ignored)
```

## Validation summary (official files)

Produced by `backend/analytics/data/validation.py`. Re-run at any time through the
Data Explorer or `GET /api/v1/dataset/quality`.

| Check | Mathematics | Portuguese |
| ----- | ----------- | ---------- |
| Expected 33 columns, documented order | pass | pass |
| Row count matches published file | 395 | 649 |
| Missing values | 0 | 0 |
| Exact duplicate rows | 0 | 0 |
| Values outside documented codes/ranges | 0 | 0 |
| Students with final grade `G3 = 0` (valid; noted) | 38 | 15 |

## Known limitations

- **No student identifier.** Row numbers are file positions, not IDs. Students in both
  cohorts can only be matched approximately (see below).
- **No dropout label.** Nothing in the data records whether a student left school. The
  project predicts final performance (`G3`) and *academic risk* (failing the final
  assessment), and makes no claim about dropout.
- **`G3 = 0`.** Valid under the documentation, but possibly a student who did not sit
  the final evaluation. Rows are kept; the handling is decided in Phase 5.
- **`failures` coding.** UCI documents "n if 1 ≤ n < 3, else 4", but the files contain
  0–3 and never 4. The value 3 is read as "3 or more".
- **Scope.** Two schools, one region, one school year (2005–2006, per the source
  paper). Findings may not generalise.

## Students in both cohorts

UCI's notes say 382 students belong to both files and give an R script that joins on
13 attributes (`school, sex, age, address, famsize, Pstatus, Medu, Fedu, Mjob, Fjob,
reason, nursery, internet`). A plain join counts a student more than once when
several students share the same 13 values. On the official files:

| Measure | Value |
| ------- | ----- |
| Rows produced by UCI's join | 382 |
| Mathematics rows with any match | 370 of 395 |
| Portuguese rows with any match | 374 of 649 |
| Profiles unique in both files (defensible one-to-one matches) | 358 |
| Matched profiles shared by several students | 8 |

The match is an **approximation** based on shared attributes. It is reported, never
used to create an identifier, and by default the two cohorts are analysed separately.
