from pathlib import Path
from typing import List

from .common import get_companies_house_api_key, get_json, write_incoming

COMPANIES_HOUSE_API = "https://api.company-information.service.gov.uk/search/companies"


def fetch_companies_house(incoming_dir: Path, query: str, limit: int = 25) -> List[Path]:
    api_key = get_companies_house_api_key()
    if not api_key:
        raise RuntimeError(
            "COMPANIES_HOUSE_API_KEY is not set — Companies House requires a free registered API key"
        )

    data = get_json(
        COMPANIES_HOUSE_API,
        params={"q": query, "items_per_page": limit},
        auth=(api_key, ""),
    )

    written: List[Path] = []
    for item in data.get("items", [])[:limit]:
        company_number = item.get("company_number")
        if not company_number:
            continue
        payload = {
            "name": item.get("title"),
            "company_number": company_number,
            "company_status": item.get("company_status"),
            "date_of_creation": item.get("date_of_creation"),
            "address_snippet": item.get("address_snippet"),
        }
        path = write_incoming(incoming_dir, "companies_house", company_number, payload)
        written.append(path)
    return written
