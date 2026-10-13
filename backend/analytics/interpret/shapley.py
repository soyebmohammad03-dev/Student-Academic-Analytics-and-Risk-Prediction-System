"""Interventional Shapley values estimated by permutation sampling.

For one record x, a model output f and a background sample of training students, the
Shapley value of attribute j is its average marginal contribution when attributes are
switched from a background student's values to x's values in a random order. This is
the estimator used by ``shap.PermutationExplainer`` (Štrumbelj & Kononenko, 2014),
implemented here so that the players are the original attributes (see
``attributes.py``) and engineered/one-hot columns always stay consistent.

Each sample draws one permutation and one background student z and walks from z to x,
recording the change in f after each attribute switches. Every sample is exactly
additive, so the estimates satisfy

    base_value + Σ contributions = f(x)

where ``base_value`` is the mean of f over the sampled background students.
Antithetic sampling (each permutation is also used reversed, with the same z) reduces
variance. The standard error of each contribution is reported. With a fixed seed the
result is deterministic. Cost: ``n_samples × (attributes + 1)`` model evaluations,
made in one batch.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from analytics.data.dictionary import COLUMNS_BY_NAME
from analytics.interpret.attributes import attributes, model_input
from analytics.preprocessing import Scenario

#: Default number of sampled permutations (half of them antithetic).
DEFAULT_SAMPLES = 128
DEFAULT_SEED = 42


@dataclass(frozen=True)
class ShapleyEstimate:
    attributes: tuple[str, ...]
    values: np.ndarray
    standard_errors: np.ndarray
    base_value: float
    prediction: float
    n_samples: int
    background_size: int


def _typed(rows: np.ndarray, names: tuple[str, ...]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            name: pd.Series(
                rows[:, i],
                dtype=object if COLUMNS_BY_NAME[name].measure == "categorical" else "float64",
            )
            for i, name in enumerate(names)
        }
    )


def shapley_values(
    output: Callable[[pd.DataFrame], np.ndarray],
    record: pd.Series,
    background: pd.DataFrame,
    scenario: Scenario,
    *,
    n_samples: int = DEFAULT_SAMPLES,
    seed: int = DEFAULT_SEED,
) -> ShapleyEstimate:
    """``output`` maps a model-input frame to one number per row.

    ``record`` and ``background`` hold raw attributes (the scenario's ``attributes``).
    """
    names = attributes(scenario)
    p = len(names)
    if n_samples < 2 or n_samples % 2:
        raise ValueError("n_samples must be an even number ≥ 2 (antithetic pairs).")
    rng = np.random.default_rng(seed)
    pairs = n_samples // 2
    forward = np.array([rng.permutation(p) for _ in range(pairs)])
    orders = np.concatenate([forward, forward[:, ::-1]])
    z_index = rng.integers(len(background), size=pairs)
    Z = background[list(names)].to_numpy(dtype=object)[np.concatenate([z_index, z_index])]
    x = record[list(names)].to_numpy(dtype=object)

    rank = np.argsort(orders, axis=1)  # rank[s, j] = position of attribute j in order s
    steps = np.arange(p + 1)
    switched = rank[:, None, :] < steps[None, :, None]  # (S, p+1, p)
    hybrid = np.where(switched, x[None, None, :], Z[:, None, :]).reshape(-1, p)

    f = np.asarray(output(model_input(_typed(hybrid, names), scenario)), dtype=float)
    f = f.reshape(n_samples, p + 1)
    deltas = np.diff(f, axis=1)  # deltas[s, k] belongs to attribute orders[s, k]
    phi = np.zeros((n_samples, p))
    np.put_along_axis(phi, orders, deltas, axis=1)

    pair_means = (phi[:pairs] + phi[pairs:]) / 2
    se = pair_means.std(axis=0, ddof=1) / np.sqrt(pairs) if pairs > 1 else np.zeros(p)
    return ShapleyEstimate(
        attributes=names,
        values=phi.mean(axis=0),
        standard_errors=se,
        base_value=float(f[:, 0].mean()),
        prediction=float(f[0, -1]),
        n_samples=n_samples,
        background_size=len(background),
    )
