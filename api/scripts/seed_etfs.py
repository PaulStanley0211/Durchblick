"""Seed the etfs table from shared/etfs.yaml.

The YAML at the repo root is the curated source of truth for
Durchblick's phase-one ETF universe. This script reads it, validates
each row with Pydantic, checks for duplicate ISINs in-process, and
upserts via INSERT ... ON CONFLICT (isin) DO UPDATE. Idempotent:
re-running upserts on the isin primary key.

Run with:
    cd api && uv run python -m scripts.seed_etfs
"""

from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import _get_engine
from app.models import Etf

REPO_SHARED_YAML = Path(__file__).resolve().parents[2] / "shared" / "etfs.yaml"


class EtfSeedRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    isin: Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")]
    name: Annotated[str, StringConstraints(min_length=1, max_length=255)]
    issuer: Annotated[str, StringConstraints(min_length=1, max_length=255)]
    ter: Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("0.05"))]
    replication_method: Literal["physical", "physical_sampling", "synthetic"]
    distribution_policy: Literal["accumulating", "distributing"]
    domicile: Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
    aum_eur: Annotated[Decimal, Field(ge=Decimal("0"))]
    inception_date: date
    index_tracked: Annotated[str, StringConstraints(min_length=1, max_length=255)]
    teilfreistellung_class: Literal["equity", "mixed", "none"]


_ROW_ADAPTER: TypeAdapter[list[EtfSeedRow]] = TypeAdapter(list[EtfSeedRow])


def _parse_yaml(path: Path) -> list[EtfSeedRow]:
    """Read the YAML at path and validate every row via Pydantic."""
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return _ROW_ADAPTER.validate_python(raw)


def _check_unique_isins(rows: list[EtfSeedRow]) -> None:
    """Raise ValueError if any ISIN appears more than once."""
    counts = Counter(row.isin for row in rows)
    duplicates = [isin for isin, count in counts.items() if count > 1]
    if duplicates:
        raise ValueError(f"Duplicate ISIN(s) in YAML: {', '.join(sorted(duplicates))}")


def seed(yaml_path: Path | None = None) -> int:
    """Upsert ETF rows from the YAML at yaml_path (default: shared/etfs.yaml).

    Returns the number of rows written.
    """
    path = yaml_path if yaml_path is not None else REPO_SHARED_YAML
    rows = _parse_yaml(path)
    _check_unique_isins(rows)

    values = [{**row.model_dump(mode="python"), "last_ingested_at": func.now()} for row in rows]
    with Session(_get_engine()) as session:
        stmt = insert(Etf).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["isin"],
            set_={
                "name": stmt.excluded.name,
                "issuer": stmt.excluded.issuer,
                "ter": stmt.excluded.ter,
                "replication_method": stmt.excluded.replication_method,
                "distribution_policy": stmt.excluded.distribution_policy,
                "domicile": stmt.excluded.domicile,
                "aum_eur": stmt.excluded.aum_eur,
                "inception_date": stmt.excluded.inception_date,
                "index_tracked": stmt.excluded.index_tracked,
                "teilfreistellung_class": stmt.excluded.teilfreistellung_class,
                "last_ingested_at": func.now(),
                "updated_at": func.now(),
            },
        )
        session.execute(stmt)
        session.commit()

    return len(rows)


if __name__ == "__main__":
    count = seed()
    print(f"Seeded {count} etfs rows.")
