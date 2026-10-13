"""Machine learning: G3 regression and academic-risk classification (Phase 5).

Modules:

- ``config``      seeds, folds, search modes
- ``registry``    model definitions, search spaces, preprocessing + estimator pipelines
- ``metrics``     regression and classification metrics (ROC-AUC from scores only)
- ``evaluation``  nested cross-validation, tuning and one-off test evaluation
- ``selection``   the model-selection rule (CV only)
- ``errors``      error analysis of the selected models
- ``training``    orchestration per cohort
- ``comparison``  standardised regression, classification, scenario and cohort tables
- ``persistence`` saving/loading results and selected pipelines
- ``predict``     validated single-record prediction service
- ``report``      docs/ML_RESULTS.md
- ``train``       CLI: ``python -m analytics.ml.train``
"""

from analytics.ml.config import CV_FOLDS, SearchMode, Task, TrainingConfig
from analytics.ml.persistence import ModelArtifactError, load_results, save
from analytics.ml.predict import (
    InvalidRecordError,
    ModelNotAvailableError,
    PredictionResult,
    PredictionService,
    record_frame,
)
from analytics.ml.registry import MODELS, ModelSpec, build_pipeline, get_spec, search_space
from analytics.ml.training import TrainedCohort, train_cohort

__all__ = [
    "CV_FOLDS",
    "MODELS",
    "InvalidRecordError",
    "ModelArtifactError",
    "ModelNotAvailableError",
    "ModelSpec",
    "PredictionResult",
    "PredictionService",
    "SearchMode",
    "Task",
    "TrainedCohort",
    "TrainingConfig",
    "build_pipeline",
    "get_spec",
    "load_results",
    "record_frame",
    "save",
    "search_space",
    "train_cohort",
]
