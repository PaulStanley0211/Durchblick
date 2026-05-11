"""Unit tests for the seed_etfs loader: YAML parsing and validation only.

These tests exercise _parse_yaml and the in-process duplicate check
without touching any database. The integration tests in
tests/integration/test_seed_etfs_db.py cover the upsert.
"""

from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.seed_etfs import REPO_SHARED_YAML, EtfSeedRow, _check_unique_isins, _parse_yaml

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"
VALID_FIXTURE = FIXTURE_DIR / "etfs_seed_sample.yaml"


def _write_yaml(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "rows.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_parse_yaml_returns_three_rows() -> None:
    rows = _parse_yaml(VALID_FIXTURE)
    assert len(rows) == 3
    assert all(isinstance(r, EtfSeedRow) for r in rows)


def test_parse_yaml_preserves_decimal_for_ter() -> None:
    rows = _parse_yaml(VALID_FIXTURE)
    # ter is Decimal in the model so on-conflict updates are exact
    assert rows[0].ter == Decimal("0.0020")


def test_parse_yaml_rejects_unknown_key(tmp_path: Path) -> None:
    bad = _write_yaml(
        tmp_path,
        """
- isin: IE00B4L5Y983
  name: Bad
  issuer: x
  tre: 0.002
  replication_method: physical
  distribution_policy: accumulating
  domicile: IE
  aum_eur: 1
  inception_date: 2020-01-01
  index_tracked: x
  teilfreistellung_class: equity
""",
    )
    with pytest.raises(ValidationError) as exc:
        _parse_yaml(bad)
    assert "tre" in str(exc.value)


def test_parse_yaml_rejects_short_isin(tmp_path: Path) -> None:
    bad = _write_yaml(
        tmp_path,
        """
- isin: IE00B4L5Y9
  name: Bad
  issuer: x
  ter: 0.002
  replication_method: physical
  distribution_policy: accumulating
  domicile: IE
  aum_eur: 1
  inception_date: 2020-01-01
  index_tracked: x
  teilfreistellung_class: equity
""",
    )
    with pytest.raises(ValidationError):
        _parse_yaml(bad)


def test_parse_yaml_rejects_excessive_ter(tmp_path: Path) -> None:
    bad = _write_yaml(
        tmp_path,
        """
- isin: IE00B4L5Y983
  name: Bad
  issuer: x
  ter: 0.20
  replication_method: physical
  distribution_policy: accumulating
  domicile: IE
  aum_eur: 1
  inception_date: 2020-01-01
  index_tracked: x
  teilfreistellung_class: equity
""",
    )
    with pytest.raises(ValidationError):
        _parse_yaml(bad)


def test_parse_yaml_rejects_unknown_teilfreistellung_class(tmp_path: Path) -> None:
    bad = _write_yaml(
        tmp_path,
        """
- isin: IE00B4L5Y983
  name: Bad
  issuer: x
  ter: 0.002
  replication_method: physical
  distribution_policy: accumulating
  domicile: IE
  aum_eur: 1
  inception_date: 2020-01-01
  index_tracked: x
  teilfreistellung_class: bond
""",
    )
    with pytest.raises(ValidationError):
        _parse_yaml(bad)


def test_check_unique_isins_raises_on_duplicate() -> None:
    rows = [
        EtfSeedRow(
            isin="IE00B4L5Y983",
            name="A",
            issuer="x",
            ter=Decimal("0.002"),
            replication_method="physical",
            distribution_policy="accumulating",
            domicile="IE",
            aum_eur=Decimal("1"),
            inception_date="2020-01-01",  # pyright: ignore[reportArgumentType]
            index_tracked="x",
            teilfreistellung_class="equity",
        ),
        EtfSeedRow(
            isin="IE00B4L5Y983",
            name="A again",
            issuer="x",
            ter=Decimal("0.002"),
            replication_method="physical",
            distribution_policy="accumulating",
            domicile="IE",
            aum_eur=Decimal("1"),
            inception_date="2020-01-01",  # pyright: ignore[reportArgumentType]
            index_tracked="x",
            teilfreistellung_class="equity",
        ),
    ]
    with pytest.raises(ValueError) as exc:
        _check_unique_isins(rows)
    assert "IE00B4L5Y983" in str(exc.value)


def test_shipped_etfs_yaml_parses_with_fifteen_rows() -> None:
    """Guardrail: the curated source-of-truth file is always loadable."""
    rows = _parse_yaml(REPO_SHARED_YAML)
    assert len(rows) == 15
    # All ISINs must be unique
    _check_unique_isins(rows)
