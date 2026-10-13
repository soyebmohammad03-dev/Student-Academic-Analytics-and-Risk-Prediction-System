"""Attributes as the unit of explanation, and readable names for encoded features.

Explanations and importances are reported per **original attribute** (a column of the
UCI file such as ``Mjob`` or ``absences``), not per encoded column. Encoded and
engineered columns are mapped back to the attribute they come from:

- one-hot columns (``Mjob_teacher``, ``higher_yes``) → ``Mjob``, ``higher``
- ``has_past_failures`` → ``failures``; ``log_absences`` → ``absences``

Perturbing an attribute therefore changes all of its encoded/engineered columns
together, so no explanation ever evaluates an impossible input such as
``failures = 2`` with ``has_past_failures = 0``.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from analytics.data.dictionary import COLUMNS_BY_NAME
from analytics.ml.predict import required_attributes
from analytics.preprocessing import Scenario, feature_columns
from analytics.preprocessing.features import ENGINEERED_FEATURES, add_engineered_features

#: Engineered feature → the raw attribute it is computed from.
ENGINEERED_SOURCE: dict[str, str] = {f.name: f.sources[0] for f in ENGINEERED_FEATURES}


def attributes(scenario: Scenario) -> tuple[str, ...]:
    """Raw attributes a model for this scenario depends on (the explanation 'players')."""
    return required_attributes(Scenario(scenario))


def attribute_label(name: str) -> str:
    return COLUMNS_BY_NAME[name].label


def value_label(name: str, value: Any) -> str:
    """Human-readable value, e.g. ``studytime = 2`` → ``2 (2 to 5 hours)``."""
    spec = COLUMNS_BY_NAME[name]
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    for allowed in spec.allowed:
        if allowed.code == value:
            return allowed.label if isinstance(value, str) else f"{value} ({allowed.label})"
    return str(value)


def encoded_attribute(name: str) -> tuple[str, str]:
    """Map an encoded feature to ``(attribute, readable label)``."""
    if name in ENGINEERED_SOURCE:
        source = ENGINEERED_SOURCE[name]
        readable = {
            "has_past_failures": "Any past failures (yes)",
            "log_absences": "Absences (log scale)",
        }.get(name, name)
        return source, readable
    if name in COLUMNS_BY_NAME:
        return name, attribute_label(name)
    for column, spec in COLUMNS_BY_NAME.items():
        prefix = f"{column}_"
        if name.startswith(prefix) and spec.measure == "categorical":
            code = name.removeprefix(prefix)
            if code in spec.allowed_codes:
                return column, f"{spec.label} = {value_label(column, code)}"
    raise KeyError(f"Cannot map encoded feature {name!r} to an attribute.")


def model_input(raw: pd.DataFrame, scenario: Scenario) -> pd.DataFrame:
    """Raw attribute rows → the scenario's model input (engineered features recomputed)."""
    frame = pd.DataFrame(
        {
            name: raw[name].astype(
                object if COLUMNS_BY_NAME[name].measure == "categorical" else "float64"
            )
            for name in attributes(scenario)
        },
        index=raw.index,
    )
    return add_engineered_features(frame)[list(feature_columns(scenario))]
