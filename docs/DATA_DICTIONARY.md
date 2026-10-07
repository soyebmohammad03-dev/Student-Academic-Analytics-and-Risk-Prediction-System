# Data Dictionary

<!-- Generated from backend/analytics/data/dictionary.py. Do not edit by hand.
     Regenerate with: cd backend && python -m analytics.data.docgen -->

UCI Student Performance dataset (ID 320). Both cohorts (`student-mat.csv`,
`student-por.csv`) share the same 33 attributes. Descriptions follow the
`student.txt` notes distributed with the dataset; *Measure* follows the UCI
classification (UCI lists coded ordinal scales such as `Medu` as numeric).

| # | Column | Description | Group | Measure | Scale | Role | Allowed values / range |
| - | ------ | ----------- | ----- | ------- | ----- | ---- | ---------------------- |
| 1 | `school` | Student's school. | Demographic | categorical | binary | Feature | `GP` Gabriel Pereira<br>`MS` Mousinho da Silveira |
| 2 | `sex` | Student's sex. | Demographic | categorical | binary | Feature | `F` Female<br>`M` Male |
| 3 | `age` | Student's age in years. | Demographic | numerical | count | Feature | 15–22 |
| 4 | `address` | Student's home address type. | Demographic | categorical | binary | Feature | `U` Urban<br>`R` Rural |
| 5 | `famsize` | Family size. | Family background | categorical | binary | Feature | `LE3` Less than or equal to 3<br>`GT3` Greater than 3 |
| 6 | `Pstatus` | Parent's cohabitation status. | Family background | categorical | binary | Feature | `T` Living together<br>`A` Apart |
| 7 | `Medu` | Mother's education level. | Family background | numerical | ordinal | Feature | `0` None<br>`1` Primary education (4th grade)<br>`2` 5th to 9th grade<br>`3` Secondary education<br>`4` Higher education |
| 8 | `Fedu` | Father's education level. | Family background | numerical | ordinal | Feature | `0` None<br>`1` Primary education (4th grade)<br>`2` 5th to 9th grade<br>`3` Secondary education<br>`4` Higher education |
| 9 | `Mjob` | Mother's job. | Family background | categorical | nominal | Feature | `teacher` Teacher<br>`health` Health care related<br>`services` Civil services (e.g. administrative or police)<br>`at_home` At home<br>`other` Other |
| 10 | `Fjob` | Father's job. | Family background | categorical | nominal | Feature | `teacher` Teacher<br>`health` Health care related<br>`services` Civil services (e.g. administrative or police)<br>`at_home` At home<br>`other` Other |
| 11 | `reason` | Reason to choose this school. | School and study | categorical | nominal | Feature | `home` Close to home<br>`reputation` School reputation<br>`course` Course preference<br>`other` Other |
| 12 | `guardian` | Student's guardian. | Family background | categorical | nominal | Feature | `mother` Mother<br>`father` Father<br>`other` Other |
| 13 | `traveltime` | Home to school travel time. | School and study | numerical | ordinal | Feature | `1` Less than 15 minutes<br>`2` 15 to 30 minutes<br>`3` 30 minutes to 1 hour<br>`4` More than 1 hour |
| 14 | `studytime` | Weekly study time. | School and study | numerical | ordinal | Feature | `1` Less than 2 hours<br>`2` 2 to 5 hours<br>`3` 5 to 10 hours<br>`4` More than 10 hours |
| 15 | `failures` | Number of past class failures (n if 1 <= n < 3, else 4). | School and study | numerical | count | Feature | 0–4 |
| 16 | `schoolsup` | Extra educational support from the school. | School and study | categorical | binary | Feature | `yes` Yes<br>`no` No |
| 17 | `famsup` | Family educational support. | Family background | categorical | binary | Feature | `yes` Yes<br>`no` No |
| 18 | `paid` | Extra paid classes within the course subject (Math or Portuguese). | School and study | categorical | binary | Feature | `yes` Yes<br>`no` No |
| 19 | `activities` | Extra-curricular activities. | Social and lifestyle | categorical | binary | Feature | `yes` Yes<br>`no` No |
| 20 | `nursery` | Attended nursery school. | School and study | categorical | binary | Feature | `yes` Yes<br>`no` No |
| 21 | `higher` | Wants to take higher education. | School and study | categorical | binary | Feature | `yes` Yes<br>`no` No |
| 22 | `internet` | Internet access at home. | Family background | categorical | binary | Feature | `yes` Yes<br>`no` No |
| 23 | `romantic` | With a romantic relationship. | Social and lifestyle | categorical | binary | Feature | `yes` Yes<br>`no` No |
| 24 | `famrel` | Quality of family relationships, from 1 (very bad) to 5 (excellent). | Family background | numerical | ordinal | Feature | `1` Very bad<br>`2` Bad<br>`3` Average<br>`4` Good<br>`5` Excellent |
| 25 | `freetime` | Free time after school, from 1 (very low) to 5 (very high). | Social and lifestyle | numerical | ordinal | Feature | `1` Very low<br>`2` Low<br>`3` Medium<br>`4` High<br>`5` Very high |
| 26 | `goout` | Going out with friends, from 1 (very low) to 5 (very high). | Social and lifestyle | numerical | ordinal | Feature | `1` Very low<br>`2` Low<br>`3` Medium<br>`4` High<br>`5` Very high |
| 27 | `Dalc` | Workday alcohol consumption, from 1 (very low) to 5 (very high). | Social and lifestyle | numerical | ordinal | Feature | `1` Very low<br>`2` Low<br>`3` Medium<br>`4` High<br>`5` Very high |
| 28 | `Walc` | Weekend alcohol consumption, from 1 (very low) to 5 (very high). | Social and lifestyle | numerical | ordinal | Feature | `1` Very low<br>`2` Low<br>`3` Medium<br>`4` High<br>`5` Very high |
| 29 | `health` | Current health status, from 1 (very bad) to 5 (very good). | Health | numerical | ordinal | Feature | `1` Very bad<br>`2` Bad<br>`3` Average<br>`4` Good<br>`5` Very good |
| 30 | `absences` | Number of school absences. | School and study | numerical | count | Feature | 0–93 |
| 31 | `G1` | First period grade in the course subject (Math or Portuguese). | Grades | numerical | grade | Prior grade | 0–20 |
| 32 | `G2` | Second period grade in the course subject (Math or Portuguese). | Grades | numerical | grade | Prior grade | 0–20 |
| 33 | `G3` | Final year grade in the course subject (Math or Portuguese); the output target. | Grades | numerical | grade | **Target** | 0–20 |

## Notes

- **`failures`**: UCI documents values of 3 or more as coded 4, but the published files contain 0-3 and no 4. Treat 3 as '3 or more' unless evidence suggests otherwise.
- **`G1`**: Known after the first period. Only a legitimate input in scenarios A and B.
- **`G2`**: Known after the second period. Only a legitimate input in scenario A.
- **`G3`**: Primary performance target. Never used as an input to predict itself or a label derived from it.
- **`G3`**: A value of 0 is within the documented range but may indicate a student who did not sit the final evaluation. Rows are kept and count as at risk (Phase 3); a sensitivity check is planned for Phase 5.

## Derived targets

Created by `backend/analytics/preprocessing/targets.py`. Outcomes only — never predictors.

| Column | Definition | Task |
| ------ | ---------- | ---- |
| `G3` | Final grade, 0–20 (as published) | Regression target |
| `at_risk` | 1 if `G3` < 10 (below the pass mark), else 0 | Classification target: academic risk, **not** dropout |

## Engineered features

Created by `backend/analytics/preprocessing/features.py`. Row-wise and stateless.

| Feature | Definition | Reason | Leakage assessment |
| ------- | ---------- | ------ | ------------------ |
| `has_past_failures` | 1 if failures > 0, else 0. | Most students have no past failures (79% in Mathematics, 85% in Portuguese), so the any-versus-none contrast is the most populated distinction in the variable. The count `failures` is kept alongside it. | None. Past class failures precede the current school year and do not use any grade from it. |
| `log_absences` | ln(1 + absences). Replaces `absences` in model inputs. | Absences are strongly right-skewed (sample skewness 3.7 in Mathematics, 2.0 in Portuguese; maxima 75 and 32). The log transform reduces the leverage of extreme counts on linear and distance-based models without removing any observation. Tree models are unaffected by this monotonic transform. | Does not use any grade. Caveat: UCI does not document the period over which absences were counted; if they accumulate over the whole year, the value is only partially known at an early-warning point. Stated as a limitation of the early scenario. |

Considered and not added:

- **grade_trend (G2 − G1)**: A linear combination of two inputs that are already present in the full-history scenario; adds collinearity without new information.
- **parent_max_edu (max of Medu, Fedu)**: Discards information that Medu and Fedu already carry individually.
- **studytime grouping**: studytime is already a 4-level ordinal code; regrouping it needs statistical evidence from Phase 4 that does not exist yet.
- **support_count (schoolsup + famsup + paid)**: Adds heterogeneous forms of support as if they were equivalent; the three indicators are kept separately.
- **alcohol composite (Dalc + Walc)**: No documented scale for combining the two ratings; both are kept as recorded.

## Analysis groupings (Phase 4)

Groups used by statistical comparisons and charts (`analytics/statistics/groups.py`).
They are fixed in advance and never tuned to results. Only these differ from raw codes:

| Grouping | Groups | Note |
| -------- | ------ | ---- |
| `absence_band` | None, 1–5, 6–10, 11–20, 21+ | Descriptive bands; the primary absence analysis uses the raw count. |
| `Medu` | Primary or less, 5th to 9th grade, Secondary, Higher education | Level 0 (none) merged with level 1 because it has very few students. |
| `Fedu` | Primary or less, 5th to 9th grade, Secondary, Higher education | Level 0 (none) merged with level 1 because it has very few students. |

## Grades

- `G1`: first-period grade, `G2`: second-period grade, `G3`: final grade.
  All are on the Portuguese 0–20 scale, where 10 is the pass mark.
- `G3` is the primary performance target. `G1` and `G2` are strongly related to it
  and are treated as *prior grades*. They are only valid inputs when a prediction is
  made after those periods (see `docs/METHODOLOGY.md`).
- The dataset contains **no dropout label**, so no attribute here measures dropout.
