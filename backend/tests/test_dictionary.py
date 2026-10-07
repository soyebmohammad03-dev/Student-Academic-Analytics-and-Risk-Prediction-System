from pathlib import Path

from analytics.data.dictionary import COLUMNS, COLUMNS_BY_NAME, TARGET
from analytics.data.docgen import to_markdown

DOC = Path(__file__).resolve().parents[2] / "docs" / "DATA_DICTIONARY.md"


def test_dictionary_covers_all_33_uci_attributes_in_order():
    assert len(COLUMNS) == 33
    assert [c.position for c in COLUMNS] == list(range(1, 34))


def test_measures_match_uci_classification():
    assert sum(c.measure == "categorical" for c in COLUMNS) == 17
    assert sum(c.measure == "numerical" for c in COLUMNS) == 16


def test_every_column_has_allowed_values_or_a_range():
    for spec in COLUMNS:
        if spec.measure == "categorical":
            assert spec.allowed, spec.name
        else:
            assert spec.minimum is not None and spec.maximum is not None, spec.name


def test_grade_roles():
    assert TARGET.name == "G3"
    assert COLUMNS_BY_NAME["G1"].role == COLUMNS_BY_NAME["G2"].role == "prior_grade"
    assert [c.name for c in COLUMNS if c.role == "target"] == ["G3"]


def test_documentation_is_generated_from_the_dictionary():
    assert DOC.read_text(encoding="utf-8") == to_markdown(), (
        "docs/DATA_DICTIONARY.md is stale: run `python -m analytics.data.docgen`"
    )
