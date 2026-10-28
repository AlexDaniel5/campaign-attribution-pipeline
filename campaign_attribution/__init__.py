"""Synthetic CRM data generator and DuckDB loader for the
campaign attribution pipeline.

All data produced here is SYNTHETIC. No real company, person, or
account data is used. The generator is deterministic given a seed so
that dbt tests and pipeline reconciliation are reproducible.
"""

from campaign_attribution.generator import generate_all, CATEGORIES
from campaign_attribution.loader import load_warehouse, RAW_SCHEMA, TABLE_DDL

__all__ = [
    "generate_all",
    "CATEGORIES",
    "load_warehouse",
    "RAW_SCHEMA",
    "TABLE_DDL",
]
