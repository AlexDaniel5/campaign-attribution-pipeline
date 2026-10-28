"""pytest suite for the synthetic data generator and DuckDB loader.

Validates schema shape, referential integrity, row counts, and the
funnel/attribution invariants the generator is responsible for
upholding. These tests run against an in-memory DuckDB so they are fast
and need no on-disk warehouse.
"""

from __future__ import annotations

import duckdb
import pytest

from campaign_attribution.generator import generate_all, CATEGORIES
from campaign_attribution.loader import load_warehouse, RAW_SCHEMA, TABLE_DDL


@pytest.fixture(scope="module")
def data():
    return generate_all(seed=42, n_campaigns=12, n_leads=1200)


@pytest.fixture(scope="module")
def con(data):
    connection = duckdb.connect(":memory:")
    load_warehouse(connection, data)
    yield connection
    connection.close()


def _count(con, table):
    return con.execute(f"select count(*) from {RAW_SCHEMA}.{table}").fetchone()[0]


# --- schema shape ---------------------------------------------------------

def test_all_tables_created(con):
    tables = {
        r[0]
        for r in con.execute(
            "select table_name from information_schema.tables "
            f"where table_schema = '{RAW_SCHEMA}'"
        ).fetchall()
    }
    assert set(TABLE_DDL.keys()) <= tables


def test_expected_columns_present(con):
    expected = {
        "raw_campaigns": {"campaign_id", "channel", "campaign_type", "budget_usd"},
        "raw_leads": {"lead_id", "is_mql", "is_converted", "converted_contact_id"},
        "raw_contacts": {"contact_id", "lead_id"},
        "raw_campaign_members": {"campaign_member_id", "campaign_id", "lead_id", "touch_date"},
        "raw_opportunities": {"opportunity_id", "contact_id", "amount_usd", "is_won"},
    }
    for table, cols in expected.items():
        actual = {
            r[0]
            for r in con.execute(
                "select column_name from information_schema.columns "
                f"where table_schema = '{RAW_SCHEMA}' and table_name = '{table}'"
            ).fetchall()
        }
        assert cols <= actual, f"{table} missing columns {cols - actual}"


# --- row counts -----------------------------------------------------------

def test_row_counts_nonzero(con):
    for table in TABLE_DDL:
        assert _count(con, table) > 0, f"{table} is empty"


def test_campaign_and_lead_counts(con):
    assert _count(con, "raw_campaigns") == 12
    assert _count(con, "raw_leads") == 1200


def test_row_counts_match_generated(con, data):
    for table, rows in data.items():
        assert _count(con, table) == len(rows)


# --- referential integrity ------------------------------------------------

def test_contacts_reference_valid_leads(con):
    orphans = con.execute(
        f"""
        select count(*) from {RAW_SCHEMA}.raw_contacts c
        left join {RAW_SCHEMA}.raw_leads l on c.lead_id = l.lead_id
        where l.lead_id is null
        """
    ).fetchone()[0]
    assert orphans == 0


def test_campaign_members_reference_valid_parents(con):
    orphan_campaigns = con.execute(
        f"""
        select count(*) from {RAW_SCHEMA}.raw_campaign_members m
        left join {RAW_SCHEMA}.raw_campaigns c on m.campaign_id = c.campaign_id
        where c.campaign_id is null
        """
    ).fetchone()[0]
    orphan_leads = con.execute(
        f"""
        select count(*) from {RAW_SCHEMA}.raw_campaign_members m
        left join {RAW_SCHEMA}.raw_leads l on m.lead_id = l.lead_id
        where l.lead_id is null
        """
    ).fetchone()[0]
    assert orphan_campaigns == 0
    assert orphan_leads == 0


def test_opportunities_reference_valid_contacts(con):
    orphans = con.execute(
        f"""
        select count(*) from {RAW_SCHEMA}.raw_opportunities o
        left join {RAW_SCHEMA}.raw_contacts c on o.contact_id = c.contact_id
        where c.contact_id is null
        """
    ).fetchone()[0]
    assert orphans == 0


def test_primary_keys_unique(con):
    pks = {
        "raw_campaigns": "campaign_id",
        "raw_leads": "lead_id",
        "raw_contacts": "contact_id",
        "raw_campaign_members": "campaign_member_id",
        "raw_opportunities": "opportunity_id",
    }
    for table, pk in pks.items():
        total, distinct = con.execute(
            f"select count({pk}), count(distinct {pk}) from {RAW_SCHEMA}.{table}"
        ).fetchone()
        assert total == distinct, f"{table}.{pk} is not unique"


# --- generator invariants -------------------------------------------------

def test_every_opportunity_has_an_attributable_touch(con):
    """Each opportunity's lead must have at least one campaign touch on or
    before the close date, otherwise attribution would drop pipeline."""
    missing = con.execute(
        f"""
        with opp_leads as (
            select o.opportunity_id, c.lead_id, o.close_date
            from {RAW_SCHEMA}.raw_opportunities o
            join {RAW_SCHEMA}.raw_contacts c on o.contact_id = c.contact_id
        )
        select count(*)
        from opp_leads ol
        where not exists (
            select 1 from {RAW_SCHEMA}.raw_campaign_members m
            where m.lead_id = ol.lead_id and m.touch_date <= ol.close_date
        )
        """
    ).fetchone()[0]
    assert missing == 0


def test_converted_leads_are_mql(con):
    """Conversion implies MQL, which keeps the funnel monotonic."""
    bad = con.execute(
        f"select count(*) from {RAW_SCHEMA}.raw_leads "
        "where is_converted and not is_mql"
    ).fetchone()[0]
    assert bad == 0


def test_converted_leads_have_contact(con):
    bad = con.execute(
        f"""
        select count(*) from {RAW_SCHEMA}.raw_leads l
        where l.is_converted
          and not exists (
            select 1 from {RAW_SCHEMA}.raw_contacts c where c.lead_id = l.lead_id
          )
        """
    ).fetchone()[0]
    assert bad == 0


def test_categorical_values_within_vocabulary(con):
    checks = {
        ("raw_campaigns", "channel"): CATEGORIES["channel"],
        ("raw_campaigns", "campaign_type"): CATEGORIES["campaign_type"],
        ("raw_leads", "lead_source"): CATEGORIES["lead_source"],
        ("raw_leads", "lead_status"): CATEGORIES["lead_status"],
        ("raw_campaign_members", "member_status"): CATEGORIES["member_status"],
        ("raw_opportunities", "stage"): CATEGORIES["opportunity_stage"],
    }
    for (table, col), allowed in checks.items():
        values = {
            r[0]
            for r in con.execute(
                f"select distinct {col} from {RAW_SCHEMA}.{table}"
            ).fetchall()
        }
        assert values <= set(allowed), f"{table}.{col} has {values - set(allowed)}"


def test_deterministic_with_seed():
    a = generate_all(seed=7, n_leads=100)
    b = generate_all(seed=7, n_leads=100)
    assert a == b


def test_opportunity_amounts_positive(con):
    bad = con.execute(
        f"select count(*) from {RAW_SCHEMA}.raw_opportunities where amount_usd <= 0"
    ).fetchone()[0]
    assert bad == 0
