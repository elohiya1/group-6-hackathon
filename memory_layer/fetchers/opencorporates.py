from pathlib import Path
from typing import List

from .common import get_json, get_opencorporates_api_key, write_incoming

OPENCORPORATES_API = "https://api.opencorporates.com/v0.4/companies/search"


def fetch_opencorporates(incoming_dir: Path, query: str, limit: int = 25) -> List[Path]:
    api_key = get_opencorporates_api_key()
    if not api_key:
        raise RuntimeError(
            "OPENCORPORATES_API_KEY is not set — OpenCorporates' unauthenticated tier is too "
            "rate-limited to be usable; register a free API token"
        )

    data = get_json(
        OPENCORPORATES_API,
        params={"q": query, "per_page": limit, "api_token": api_key},
    )

    written: List[Path] = []
    companies = data.get("results", {}).get("companies", [])
    for entry in companies[:limit]:
        company = entry.get("company", {})
        company_number = company.get("company_number")
        if not company_number:
            continue
        payload = {
            "name": company.get("name"),
            "company_number": company_number,
            "jurisdiction_code": company.get("jurisdiction_code"),
            "current_status": company.get("current_status"),
            "incorporation_date": company.get("incorporation_date"),
        }
        path = write_incoming(incoming_dir, "opencorporates", company_number, payload)
        written.append(path)
    return written
