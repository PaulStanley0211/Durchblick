"""Public surface of the tax module.

Phase 9 imports only from app.tax, never from app.tax.engine or
app.tax.primitives directly. Implementation modules are private.
"""

from app.tax.constants import TaxConstantsSnapshot, lookup_year_with_fallback
from app.tax.engine import compute_lump_sum_outcome, compute_sparplan_outcome
from app.tax.outcome import TaxOutcome, VorabpauschaleYear

__all__ = [
    "TaxConstantsSnapshot",
    "TaxOutcome",
    "VorabpauschaleYear",
    "compute_lump_sum_outcome",
    "compute_sparplan_outcome",
    "lookup_year_with_fallback",
]
