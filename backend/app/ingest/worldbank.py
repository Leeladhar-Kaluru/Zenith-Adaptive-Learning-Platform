"""World Bank Open Data (CC BY 4.0) through its public API."""
from __future__ import annotations

import json
import uuid

from sqlalchemy.orm import Session

from app.ingest.datasets import DatasetError, import_dataset
from app.ingest.fetch import fetch
from app.models import SourceAsset

API = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?format=json&per_page=100"
USER_AGENT = "ZenithEducationBot/1.0 (school learning platform; respects robots.txt)"


def import_indicator(db: Session, indicator: str, country: str, title: str, actor_id: uuid.UUID | None) -> SourceAsset:
    data = json.loads(fetch(API.format(country=country, indicator=indicator), user_agent=USER_AGENT))
    if not isinstance(data, list) or len(data) < 2 or not isinstance(data[1], list):
        raise DatasetError("The World Bank answered in an unexpected shape.")
    rows = sorted(({"year": int(r["date"]), "value": r["value"]} for r in data[1] if r.get("value") is not None), key=lambda r: r["year"])
    if not rows:
        raise DatasetError("The World Bank has no values for that indicator and country.")
    spec = dict(source_name="World Bank Open Data", source_homepage="https://data.worldbank.org", external_id=f"{indicator}:{country}", title=title,
                url=f"https://data.worldbank.org/indicator/{indicator}?locations={country}", licence="CC-BY-4.0",
                attribution=f"World Bank, {title} ({indicator}), {country}, CC BY 4.0", fields=["year", "value"], rows=rows)
    return import_dataset(db, spec, actor_id)
