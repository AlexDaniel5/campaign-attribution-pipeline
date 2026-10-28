"""CLI entry point: generate synthetic data and load it into DuckDB.

Usage:
    python -m campaign_attribution.build_warehouse --db warehouse.duckdb --seed 42
"""

from __future__ import annotations

import argparse
import os

import duckdb

from campaign_attribution.generator import generate_all
from campaign_attribution.loader import load_warehouse


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the synthetic CRM DuckDB warehouse (raw schema)."
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("DUCKDB_PATH", "warehouse.duckdb"),
        help="Path to the DuckDB database file to create/populate.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument(
        "--leads", type=int, default=1200, help="Number of synthetic leads."
    )
    parser.add_argument(
        "--campaigns", type=int, default=12, help="Number of synthetic campaigns."
    )
    args = parser.parse_args()

    data = generate_all(
        seed=args.seed, n_campaigns=args.campaigns, n_leads=args.leads
    )

    con = duckdb.connect(args.db)
    try:
        counts = load_warehouse(con, data)
    finally:
        con.close()

    print(f"Loaded synthetic CRM data into {args.db} (schema: raw)")
    for table, n in counts.items():
        print(f"  {table:<22} {n:>6} rows")
    print("NOTE: all data is synthetic; no real company data is used.")


if __name__ == "__main__":
    main()
