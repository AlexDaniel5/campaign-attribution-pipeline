"""Deterministic synthetic CRM data generator.

Produces Salesforce / Marketo shaped objects:

    campaigns, leads, contacts, campaign_members, opportunities

The data is internally consistent so that attribution and funnel
models have clean referential integrity:

  - every contact traces back to a lead
  - every opportunity traces back to a contact (whose lead converted)
  - every converting lead has at least one campaign_member (touch)
    dated on or before the opportunity close date, so every
    opportunity has at least one attributable touch
  - a lead that converted to an opportunity is always an MQL, which
    keeps the demand-generation funnel monotonic per campaign
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Controlled vocabularies. These lists are the single source of truth for the
# dbt accepted_values tests, so keep them in sync with models/staging/*.yml.
# ---------------------------------------------------------------------------
CATEGORIES: Dict[str, List[str]] = {
    "channel": [
        "Email",
        "Paid Search",
        "Paid Social",
        "Webinar",
        "Content Syndication",
        "Organic Search",
        "Events",
        "Referral",
    ],
    "campaign_type": ["Inbound", "Outbound", "Nurture", "Field", "Partner"],
    "lead_source": [
        "Website",
        "Webinar",
        "Trade Show",
        "Content",
        "Referral",
        "Cold Outreach",
        "Social",
    ],
    "lead_status": [
        "New",
        "Working",
        "Nurture",
        "MQL",
        "Converted",
        "Disqualified",
    ],
    "member_status": [
        "Sent",
        "Delivered",
        "Opened",
        "Clicked",
        "Responded",
        "Registered",
        "Attended",
    ],
    "opportunity_stage": [
        "Prospecting",
        "Qualification",
        "Proposal",
        "Negotiation",
        "Closed Won",
        "Closed Lost",
    ],
}

# Synthetic, obviously-fake company and person tokens.
_COMPANY_PREFIX = [
    "Acme", "Globex", "Initech", "Umbrella", "Soylent", "Hooli", "Vandelay",
    "Stark", "Wayne", "Wonka", "Cyberdyne", "Tyrell", "Gekko", "Oscorp",
]
_COMPANY_SUFFIX = ["Labs", "Systems", "Analytics", "Group", "Digital", "Cloud", "Works"]
_FIRST_NAMES = [
    "Avery", "Blake", "Casey", "Drew", "Emerson", "Finley", "Gray", "Harper",
    "Indigo", "Jordan", "Kai", "Logan", "Morgan", "Noel", "Quinn", "Riley",
    "Sage", "Taylor", "Val", "Wren",
]
_LAST_NAMES = [
    "Adler", "Boone", "Crane", "Dunn", "Ellis", "Frost", "Grant", "Hale",
    "Irwin", "Judd", "Keller", "Lowe", "Mercer", "Nash", "Odom", "Pike",
    "Reese", "Shaw", "Tate", "Vaughn",
]
_TITLES = [
    "Marketing Manager", "Demand Gen Lead", "VP Marketing", "Growth Analyst",
    "Director of Ops", "RevOps Manager", "CMO", "Marketing Analyst",
]


def _company(rng: random.Random) -> str:
    return f"{rng.choice(_COMPANY_PREFIX)} {rng.choice(_COMPANY_SUFFIX)}"


def _person(rng: random.Random) -> tuple[str, str]:
    return rng.choice(_FIRST_NAMES), rng.choice(_LAST_NAMES)


def generate_all(
    seed: int = 42,
    n_campaigns: int = 12,
    n_leads: int = 1200,
) -> Dict[str, List[Dict[str, Any]]]:
    """Generate all raw objects and return them keyed by table name.

    Every value is synthetic. The same ``seed`` always yields identical
    output, which is what makes the downstream reconciliation tests
    deterministic.
    """
    rng = random.Random(seed)
    today = date(2026, 10, 24)

    # -- campaigns ----------------------------------------------------------
    campaigns: List[Dict[str, Any]] = []
    for cid in range(1, n_campaigns + 1):
        channel = rng.choice(CATEGORIES["channel"])
        start = today - timedelta(days=rng.randint(120, 540))
        end = start + timedelta(days=rng.randint(30, 120))
        campaigns.append(
            {
                "campaign_id": cid,
                "campaign_name": f"{channel} {start.year}-Q{(start.month - 1) // 3 + 1} #{cid}",
                "channel": channel,
                "campaign_type": rng.choice(CATEGORIES["campaign_type"]),
                "start_date": start,
                "end_date": end,
                "budget_usd": float(rng.randint(5, 120) * 1000),
                "is_active": end >= today,
            }
        )

    # -- leads --------------------------------------------------------------
    leads: List[Dict[str, Any]] = []
    contacts: List[Dict[str, Any]] = []
    campaign_members: List[Dict[str, Any]] = []
    opportunities: List[Dict[str, Any]] = []

    member_id = 0
    contact_id = 0
    opp_id = 0

    for lid in range(1, n_leads + 1):
        first, last = _person(rng)
        company = _company(rng)
        created = today - timedelta(days=rng.randint(30, 400))
        domain = company.lower().replace(" ", "") + ".example"
        email = f"{first.lower()}.{last.lower()}{lid}@{domain}"

        # Funnel progression probabilities.
        is_mql = rng.random() < 0.55
        is_converted = is_mql and rng.random() < 0.55  # conversion requires MQL

        mql_date = None
        converted_date = None
        converted_contact_id = None

        if is_mql:
            mql_date = created + timedelta(days=rng.randint(1, 30))

        # Every lead gets 1..4 campaign touches, dated on/after creation and,
        # for converting leads, on/before the conversion date.
        n_touches = rng.randint(1, 4)
        touch_campaigns = rng.sample(
            range(1, n_campaigns + 1), k=min(n_touches, n_campaigns)
        )
        touch_dates: List[date] = []
        for _ in touch_campaigns:
            touch_dates.append(created + timedelta(days=rng.randint(0, 20)))
        touch_dates.sort()

        if is_converted:
            # conversion happens after the last recorded touch
            last_touch = max(touch_dates)
            converted_date = last_touch + timedelta(days=rng.randint(1, 20))
            if mql_date is None or mql_date > converted_date:
                mql_date = converted_date - timedelta(days=1)
            contact_id += 1
            converted_contact_id = contact_id
            contacts.append(
                {
                    "contact_id": contact_id,
                    "lead_id": lid,
                    "first_name": first,
                    "last_name": last,
                    "email": email,
                    "company": company,
                    "title": rng.choice(_TITLES),
                    "created_date": converted_date,
                }
            )

        for cid, tdate in zip(touch_campaigns, touch_dates):
            member_id += 1
            campaign_members.append(
                {
                    "campaign_member_id": member_id,
                    "campaign_id": cid,
                    "lead_id": lid,
                    "member_status": rng.choice(CATEGORIES["member_status"]),
                    "is_responded": rng.random() < 0.4,
                    "touch_date": tdate,
                }
            )

        if is_converted:
            status = "Converted"
        elif is_mql:
            status = "MQL"
        else:
            status = rng.choice(["New", "Working", "Nurture", "Disqualified"])

        leads.append(
            {
                "lead_id": lid,
                "first_name": first,
                "last_name": last,
                "email": email,
                "company": company,
                "title": rng.choice(_TITLES),
                "lead_source": rng.choice(CATEGORIES["lead_source"]),
                "created_date": created,
                "lead_status": status,
                "is_mql": is_mql,
                "mql_date": mql_date,
                "is_converted": is_converted,
                "converted_date": converted_date,
                "converted_contact_id": converted_contact_id,
            }
        )

        # -- opportunities (most converted contacts generate one) ----------
        if is_converted and rng.random() < 0.8:
            opp_id += 1
            opp_created = converted_date + timedelta(days=rng.randint(1, 20))
            is_closed = rng.random() < 0.75
            is_won = is_closed and rng.random() < 0.55
            if is_closed:
                stage = "Closed Won" if is_won else "Closed Lost"
                close_date = opp_created + timedelta(days=rng.randint(10, 90))
            else:
                stage = rng.choice(
                    ["Prospecting", "Qualification", "Proposal", "Negotiation"]
                )
                # open opps still get a (future) expected close date
                close_date = opp_created + timedelta(days=rng.randint(30, 120))
            opportunities.append(
                {
                    "opportunity_id": opp_id,
                    "contact_id": converted_contact_id,
                    "opportunity_name": f"{company} - New Business #{opp_id}",
                    "stage": stage,
                    "amount_usd": float(rng.randint(5, 250) * 1000),
                    "created_date": opp_created,
                    "close_date": close_date,
                    "is_closed": is_closed,
                    "is_won": is_won,
                }
            )

    return {
        "raw_campaigns": campaigns,
        "raw_leads": leads,
        "raw_contacts": contacts,
        "raw_campaign_members": campaign_members,
        "raw_opportunities": opportunities,
    }
