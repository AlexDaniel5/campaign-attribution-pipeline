"""Load generated synthetic data into a DuckDB warehouse (raw schema).

The raw tables mirror the shape of Salesforce / Marketo exports. dbt
sources (see models/staging/_sources.yml) read from this ``raw`` schema
and transform raw -> staging -> marts.
"""

from __future__ import annotations

from typing import Any, Dict, List

import duckdb

RAW_SCHEMA = "raw"

# Column order matters: it must match the INSERT statements built below.
TABLE_DDL: Dict[str, str] = {
    "raw_campaigns": """
        campaign_id      INTEGER,
        campaign_name    VARCHAR,
        channel          VARCHAR,
        campaign_type    VARCHAR,
        start_date       DATE,
        end_date         DATE,
        budget_usd       DOUBLE,
        is_active        BOOLEAN
    """,
    "raw_leads": """
        lead_id               INTEGER,
        first_name            VARCHAR,
        last_name             VARCHAR,
        email                 VARCHAR,
        company               VARCHAR,
        title                 VARCHAR,
        lead_source           VARCHAR,
        created_date          DATE,
        lead_status           VARCHAR,
        is_mql                BOOLEAN,
        mql_date              DATE,
        is_converted          BOOLEAN,
        converted_date        DATE,
        converted_contact_id  INTEGER
    """,
    "raw_contacts": """
        contact_id    INTEGER,
        lead_id       INTEGER,
        first_name    VARCHAR,
        last_name     VARCHAR,
        email         VARCHAR,
        company       VARCHAR,
        title         VARCHAR,
        created_date  DATE
    """,
    "raw_campaign_members": """
        campaign_member_id  INTEGER,
        campaign_id         INTEGER,
        lead_id             INTEGER,
        member_status       VARCHAR,
        is_responded        BOOLEAN,
        touch_date          DATE
    """,
    "raw_opportunities": """
        opportunity_id    INTEGER,
        contact_id        INTEGER,
        opportunity_name  VARCHAR,
        stage             VARCHAR,
        amount_usd        DOUBLE,
        created_date      DATE,
        close_date        DATE,
        is_closed         BOOLEAN,
        is_won            BOOLEAN
    """,
}


def _columns(ddl: str) -> List[str]:
    cols = []
    for line in ddl.strip().splitlines():
        line = line.strip().rstrip(",")
        if line:
            cols.append(line.split()[0])
    return cols


def load_warehouse(
    con: duckdb.DuckDBPyConnection,
    data: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, int]:
    """Create the raw schema and tables, then insert all rows.

    Returns a mapping of table name -> row count loaded.
    """
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {RAW_SCHEMA}")
    row_counts: Dict[str, int] = {}

    for table, ddl in TABLE_DDL.items():
        fqtn = f"{RAW_SCHEMA}.{table}"
        con.execute(f"DROP TABLE IF EXISTS {fqtn}")
        con.execute(f"CREATE TABLE {fqtn} ({ddl})")

        cols = _columns(ddl)
        rows = data[table]
        if rows:
            placeholders = ", ".join(["?"] * len(cols))
            insert_sql = f"INSERT INTO {fqtn} ({', '.join(cols)}) VALUES ({placeholders})"
            con.executemany(
                insert_sql, [[row[c] for c in cols] for row in rows]
            )
        row_counts[table] = len(rows)

    return row_counts
