"""Model definitions: estimators, hyperparameter search spaces and pipelines.

Every model is wrapped in a single scikit-learn ``Pipeline`` whose first stage is the
Phase 3 preprocessor for its scenario. Fitting the pipeline fits imputers, encoders and
scalers, so whenever a pipeline is fitted on a cross-validation training fold, the
preprocessing is learned from that fold only.

Search spaces are deliberately compact (the training sets have 316 and 519 students):

- **Linear regression** has no hyperparameters worth tuning here; it is fitted as is.
- **Decision trees** are tuned on depth and minimum split/leaf sizes, which control
  over-fitting.
- **Random forests** are tuned on the number of trees, depth, minimum split/leaf sizes
  and the share of features tried at each split.
- **Logistic regression** is tuned on the inverse regularisation strength ``C`` (46
  encoded features for ≈ 300–500 students).
- **k-nearest neighbours** is tuned on ``k`` and distance weighting.
- **SVM** (RBF kernel) is tuned on ``C`` and ``gamma``.

``class_weight="balanced"`` is used by every classifier that supports it, because the
at-risk class is the minority in both cohorts (33% and 15%). k-NN has no class weights;
its imbalance handling is left at the default and its recall is reported as measured.
No resampling is used.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sklearn.base import BaseEstimator
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from analytics.ml.config import SearchMode, Task
from analytics.preprocessing import Scenario, build_preprocessor

ESTIMATOR_STEP = "model"


@dataclass(frozen=True)
class ModelSpec:
    key: str
    label: str
    task: Task
    family: str
    #: Builds the unfitted estimator for a given random seed.
    factory: Callable[[int], BaseEstimator]
    #: Standardise ordinal/numeric inputs (linear, distance and kernel models).
    scale_numeric: bool
    #: Search space for the estimator's own parameters (without the pipeline prefix).
    grid: dict[str, list[Any]] = field(default_factory=dict)
    #: Lower ranks are simpler / easier to interpret; used to break near-ties.
    complexity: int = 0
    baseline: bool = False
    class_weight: str | None = None
    #: How classification scores for ROC-AUC are obtained.
    score_method: str | None = None
    strengths: str = ""
    weaknesses: str = ""


REGRESSION_MODELS: tuple[ModelSpec, ...] = (
    ModelSpec(
        key="mean_baseline",
        label="Mean baseline",
        task=Task.REGRESSION,
        family="Baseline",
        factory=lambda seed: DummyRegressor(strategy="mean"),
        scale_numeric=False,
        complexity=0,
        baseline=True,
        strengths="Predicts the training-set mean grade for everyone; the reference to beat.",
        weaknesses="Uses no information about the student.",
    ),
    ModelSpec(
        key="linear_regression",
        label="Linear regression",
        task=Task.REGRESSION,
        family="Linear",
        factory=lambda seed: LinearRegression(),
        scale_numeric=True,
        complexity=1,
        strengths="Transparent additive model; stable with few observations; no tuning.",
        weaknesses=(
            "Assumes additive, linear effects. Nominal attributes are fully one-hot "
            "encoded, so individual coefficients are not uniquely identified (the "
            "least-squares solver returns the minimum-norm solution); predictions are "
            "unaffected."
        ),
    ),
    ModelSpec(
        key="decision_tree",
        label="Decision tree",
        task=Task.REGRESSION,
        family="Tree",
        factory=lambda seed: DecisionTreeRegressor(random_state=seed),
        scale_numeric=False,
        grid={
            "max_depth": [3, 5, 8, None],
            "min_samples_split": [2, 10, 20],
            "min_samples_leaf": [1, 5, 10],
        },
        complexity=2,
        strengths="Captures thresholds and interactions; readable when shallow.",
        weaknesses="High variance: small changes in the data can change the tree.",
    ),
    ModelSpec(
        key="random_forest",
        label="Random forest",
        task=Task.REGRESSION,
        family="Ensemble",
        factory=lambda seed: RandomForestRegressor(random_state=seed, n_jobs=1),
        scale_numeric=False,
        grid={
            "n_estimators": [100, 300],
            "max_depth": [None, 8],
            "min_samples_split": [2, 10],
            "min_samples_leaf": [1, 4],
            "max_features": [1.0, 0.33],
        },
        complexity=3,
        strengths="Averages many trees: lower variance than one tree, models interactions.",
        weaknesses="Less transparent; predictions are shrunk towards the mean at the extremes.",
    ),
)

CLASSIFICATION_MODELS: tuple[ModelSpec, ...] = (
    ModelSpec(
        key="majority_baseline",
        label="Majority-class baseline",
        task=Task.CLASSIFICATION,
        family="Baseline",
        factory=lambda seed: DummyClassifier(strategy="most_frequent", random_state=seed),
        scale_numeric=False,
        complexity=0,
        baseline=True,
        score_method="predict_proba",
        strengths="Predicts 'not at risk' for everyone; shows what accuracy means here.",
        weaknesses="Identifies no at-risk student (recall 0).",
    ),
    ModelSpec(
        key="logistic_regression",
        label="Logistic regression",
        task=Task.CLASSIFICATION,
        family="Linear",
        factory=lambda seed: LogisticRegression(
            class_weight="balanced", max_iter=5000, random_state=seed
        ),
        scale_numeric=True,
        grid={"C": [0.01, 0.1, 1.0, 10.0]},
        complexity=1,
        class_weight="balanced",
        score_method="predict_proba",
        strengths="Transparent, well-calibrated probabilities; regularisation handles 46 inputs.",
        weaknesses="Linear decision boundary on the encoded inputs.",
    ),
    ModelSpec(
        key="decision_tree",
        label="Decision tree",
        task=Task.CLASSIFICATION,
        family="Tree",
        factory=lambda seed: DecisionTreeClassifier(class_weight="balanced", random_state=seed),
        scale_numeric=False,
        grid={
            "max_depth": [3, 5, 8, None],
            "min_samples_split": [2, 10, 20],
            "min_samples_leaf": [1, 5, 10],
        },
        complexity=2,
        class_weight="balanced",
        score_method="predict_proba",
        strengths="Readable rules; captures thresholds such as grade cut-offs.",
        weaknesses="High variance; coarse probability estimates (leaf proportions).",
    ),
    ModelSpec(
        key="knn",
        label="k-nearest neighbours",
        task=Task.CLASSIFICATION,
        family="Distance",
        factory=lambda seed: KNeighborsClassifier(),
        scale_numeric=True,
        grid={"n_neighbors": [5, 11, 21, 31], "weights": ["uniform", "distance"]},
        complexity=3,
        score_method="predict_proba",
        strengths="No model assumptions; local similarity between students.",
        weaknesses=(
            "No class weighting, so the minority at-risk class can be under-detected; "
            "distances over many one-hot columns are hard to interpret."
        ),
    ),
    ModelSpec(
        key="svm",
        label="Support vector machine (RBF)",
        task=Task.CLASSIFICATION,
        family="Kernel",
        factory=lambda seed: SVC(kernel="rbf", class_weight="balanced", random_state=seed),
        scale_numeric=True,
        grid={"C": [0.1, 1.0, 10.0], "gamma": ["scale", 0.01]},
        complexity=4,
        class_weight="balanced",
        score_method="decision_function",
        strengths="Flexible non-linear boundary with margin-based regularisation.",
        weaknesses=(
            "Outputs decision scores, not probabilities (ROC-AUC uses the scores); "
            "least interpretable model here."
        ),
    ),
    ModelSpec(
        key="random_forest",
        label="Random forest",
        task=Task.CLASSIFICATION,
        family="Ensemble",
        factory=lambda seed: RandomForestClassifier(
            class_weight="balanced", random_state=seed, n_jobs=1
        ),
        scale_numeric=False,
        grid={
            "n_estimators": [100, 300],
            "max_depth": [None, 8],
            "min_samples_split": [2, 10],
            "min_samples_leaf": [1, 4],
            "max_features": ["sqrt", 0.33],
        },
        complexity=5,
        class_weight="balanced",
        score_method="predict_proba",
        strengths="Robust to noise and interactions; usually strong ranking (ROC-AUC).",
        weaknesses="Less transparent; probabilities from vote shares are not calibrated.",
    ),
)

MODELS: dict[Task, tuple[ModelSpec, ...]] = {
    Task.REGRESSION: REGRESSION_MODELS,
    Task.CLASSIFICATION: CLASSIFICATION_MODELS,
}


def get_spec(task: Task, key: str) -> ModelSpec:
    for spec in MODELS[Task(task)]:
        if spec.key == key:
            return spec
    raise KeyError(f"Unknown {task} model: {key}")


def search_space(spec: ModelSpec, mode: SearchMode = SearchMode.FULL) -> dict[str, list[Any]]:
    """Grid for the pipeline (parameters prefixed with the estimator step name)."""
    grid = spec.grid
    if mode is SearchMode.MINIMAL:
        grid = {name: values[:1] for name, values in grid.items()}
        if "n_estimators" in grid:
            grid["n_estimators"] = [25]
    return {f"{ESTIMATOR_STEP}__{name}": list(values) for name, values in grid.items()}


def build_pipeline(spec: ModelSpec, scenario: Scenario, random_state: int) -> Pipeline:
    """Unfitted preprocessing + estimator pipeline for one scenario."""
    return Pipeline(
        [
            ("prep", build_preprocessor(scenario, scale_numeric=spec.scale_numeric)),
            (ESTIMATOR_STEP, spec.factory(random_state)),
        ]
    )
