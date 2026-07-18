import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List

from .common import get_text, write_incoming

ARXIV_API = "http://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"


def _parse_entry(entry: ET.Element) -> dict:
    title = entry.findtext(f"{ATOM_NS}title", default="").strip()
    published = entry.findtext(f"{ATOM_NS}published", default="")
    arxiv_id = entry.findtext(f"{ATOM_NS}id", default="")
    authors = [
        name.text
        for author in entry.findall(f"{ATOM_NS}author")
        for name in author.findall(f"{ATOM_NS}name")
        if name.text
    ]
    categories = [
        cat.get("term")
        for cat in entry.findall(f"{ATOM_NS}category")
        if cat.get("term")
    ]
    first_author = authors[0] if authors else None
    return {
        "name": first_author,
        "arxiv_id": arxiv_id,
        "title": title,
        "published": published,
        "authors": authors,
        "first_author": first_author,
        "categories": categories,
    }


def fetch_arxiv(
    incoming_dir: Path, categories: List[str], max_results: int = 50
) -> List[Path]:
    search_query = " OR ".join(f"cat:{category}" for category in categories)
    raw_xml = get_text(
        ARXIV_API,
        params={
            "search_query": search_query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": max_results,
        },
    )
    root = ET.fromstring(raw_xml)

    written: List[Path] = []
    for entry in root.findall(f"{ATOM_NS}entry")[:max_results]:
        paper = _parse_entry(entry)
        if not paper["first_author"]:
            continue
        slug = paper["arxiv_id"] or paper["title"]
        path = write_incoming(incoming_dir, "arxiv", slug, paper)
        written.append(path)
    return written
