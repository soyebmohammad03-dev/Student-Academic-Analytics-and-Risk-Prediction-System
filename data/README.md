# Data

Datasets are **not committed** to this repository. Only this README and the
`.gitkeep` placeholders are tracked.

## Primary dataset — UCI Student Performance

- Source: <https://archive.ics.uci.edu/dataset/320/student+performance>
- Licence: CC BY 4.0
- Citation: Cortez, P., & Silva, A. M. G. (2008). *Using Data Mining to Predict
  Secondary School Student Performance.* In Proceedings of the 5th Future Business
  Technology Conference (FUBUTEC 2008), pp. 5–12.

Two secondary-school cohorts from Portugal:

| File              | Subject    | Records | Attributes |
| ----------------- | ---------- | ------- | ---------- |
| `student-mat.csv` | Mathematics | 395    | 33         |
| `student-por.csv` | Portuguese  | 649    | 33         |

Files are semicolon-separated. Attributes cover demographics, family background,
study habits, social behaviour, absences, past failures and three period grades
(`G1`, `G2`, `G3`, on a 0–20 scale). Some students appear in both files.

### Important modelling note

`G1` and `G2` are strongly correlated with the final grade `G3`. Any target derived
from `G3` (for example an *academic-risk* label) must not be predicted using `G3`
itself, and the availability of `G1`/`G2` at prediction time must be stated
explicitly for each experiment. This dataset contains **no dropout label**, so the
project uses the term *academic risk*, not *dropout*. See
[`../docs/METHODOLOGY.md`](../docs/METHODOLOGY.md).

## Layout

```
data/
├── raw/         # Original, unmodified files from UCI (git-ignored)
└── processed/   # Outputs of the preprocessing pipeline (git-ignored)
```

## Obtaining the data

Download the archive from the UCI page above and place `student-mat.csv` and
`student-por.csv` in `data/raw/`. A scripted, checksum-verified download step is
planned for Phase 2.
