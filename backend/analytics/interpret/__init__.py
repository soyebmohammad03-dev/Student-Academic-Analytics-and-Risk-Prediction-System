"""Interpretability of the selected models (Phase 6).

- ``attributes``  original attributes as explanation units; readable encoded names
- ``shapley``     interventional Shapley values by permutation sampling
- ``importance``  permutation, mean |Shapley|, impurity and coefficient importance
- ``explain``     individual explanations and model-sensitivity experiments
- ``build``       CLI: ``python -m analytics.interpret.build``
- ``report``      docs/INTERPRETABILITY.md
"""

from analytics.interpret.explain import SENSITIVITY_ATTRIBUTES, CohortData, Interpreter
from analytics.interpret.shapley import shapley_values

__all__ = ["SENSITIVITY_ATTRIBUTES", "CohortData", "Interpreter", "shapley_values"]
