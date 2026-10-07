"""Offline analytics pipeline, independent of the web layer.

Subpackages (implemented in later phases):

- ``data``           dataset loading and schema validation
- ``statistics``     descriptive, correlation and inferential statistics
- ``eda``            exploratory summaries that feed the frontend charts
- ``preprocessing``  reproducible cleaning, encoding and feature engineering
- ``modeling``       target definitions, training, evaluation and artifact persistence

The FastAPI app imports from here; this package never imports from ``app``.
"""
