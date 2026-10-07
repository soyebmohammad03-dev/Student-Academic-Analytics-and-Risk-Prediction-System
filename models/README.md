# Models

Trained model artifacts are written here by the offline training pipeline
(`backend/analytics/modeling`, Phase 6) and loaded read-only by the API for inference.

Artifacts (`*.joblib`, `*.pkl`, metrics JSON) are git-ignored. Each saved model will be
accompanied by a metadata file recording the target definition, feature set,
preprocessing version, random seed and evaluation results, so every prediction can be
traced back to how the model was produced.

No models have been trained yet.
