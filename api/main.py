import logging
import os
import time
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from funnel.applications_repo import get_application
from funnel.intake import submit_application
from funnel.screen import screen_application
from intelligence.pipeline import run_intelligence
from intelligence.thesis_repo import get_thesis, set_thesis
from memory_layer.entity_resolution import find_candidate_entities, resolve_entity
from memory_layer.founder_score import compute_founder_score
from memory_layer.normalize import normalize_raw_record
from memory_layer.trust_score import compute_trust_scores

from .db import db_lock, get_conn
from .serializers import (
    build_company,
    build_founder,
    build_opportunity,
    list_application_ids,
)

logger = logging.getLogger("vc_brain.api")
logging.basicConfig(level=logging.INFO)

DECK_DIR = Path("data/decks")

DEFAULT_THESIS = {
    "sectors": ["AI infra", "Applied AI", "Developer tools"],
    "stage": "Pre-seed / Seed",
    "geography": ["EU", "US"],
    "check_size_min": 100_000.0,
    "check_size_max": 100_000.0,
    "ownership_target_pct": 5.0,
    "risk_appetite": "High",
}

_default_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:4173",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4173",
    "http://127.0.0.1:8080",
]
_extra_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]

app = FastAPI(title="VC Brain API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True}


# --- opportunities --------------------------------------------------------


@app.get("/api/opportunities")
def list_opportunities():
    with db_lock:
        conn = get_conn()
        return [build_opportunity(conn, i) for i in list_application_ids(conn)]


@app.get("/api/opportunities/search")
def search_opportunities(q: str = ""):
    query = q.strip().lower()
    if not query:
        return []
    terms = query.split()

    with db_lock:
        conn = get_conn()
        opportunities = [build_opportunity(conn, i) for i in list_application_ids(conn)]

    results = []
    for o in opportunities:
        matches: set[str] = set()

        def push(label: str, hay: Optional[str]) -> None:
            hay_lower = (hay or "").lower()
            if any(t in hay_lower for t in terms):
                matches.add(label)

        push("company_name", o["company_name"])
        if o["founder"]:
            push("founder", o["founder"]["canonical_name"])
        if o["thesis_fit"]:
            push("thesis_rationale", o["thesis_fit"]["rationale"])
        for a in o["axes"] or []:
            push(f"axis:{a['axis']}", a["rationale"])
        if o["founder"]:
            for d in o["founder"]["data_points"]:
                push(d["attribute_name"], f"{d['value']} {d['source_name']}")

        if matches:
            results.append({"opportunity": o, "matched_attributes": sorted(matches)})
    return results


@app.get("/api/opportunities/{application_id}")
def get_opportunity(application_id: int):
    with db_lock:
        conn = get_conn()
        opportunity = build_opportunity(conn, application_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return opportunity


@app.post("/api/applications", status_code=201)
def create_application(
    company_name: str = Form(...),
    deck: UploadFile = File(...),
    founder_email: Optional[str] = Form(None),
    github_username: Optional[str] = Form(None),
    company_domain: Optional[str] = Form(None),
):
    with db_lock:
        conn = get_conn()
        DECK_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = f"{int(time.time() * 1000)}_{deck.filename or 'deck'}"
        deck_path = DECK_DIR / safe_name
        deck_path.write_bytes(deck.file.read())

        application_id = submit_application(
            conn,
            company_name,
            deck_path,
            company_domain=company_domain or None,
            founder_email=founder_email or None,
            founder_github=github_username or None,
        )

        try:
            screen_application(conn, application_id)
        except Exception:
            logger.exception("screening failed for application %s", application_id)

        status = get_application(conn, application_id)[6]
        if status == "screened_pass":
            try:
                run_intelligence(conn, application_id)
            except Exception:
                # Best-effort: without a valid OPENAI_API_KEY (or on API
                # failure) the application still exists as screened_pass;
                # the frontend already renders "not yet analyzed" for that.
                logger.exception("intelligence pass failed for application %s", application_id)

        opportunity = build_opportunity(conn, application_id)
    return opportunity


# --- outbound signals ------------------------------------------------------


@app.get("/api/outbound-signals")
def list_outbound_signals():
    with db_lock:
        conn = get_conn()
        rows = conn.execute(
            "SELECT os.id, e.canonical_name, os.conviction_score, os.status, os.detected_at, "
            "os.entity_id FROM outbound_signals os JOIN entities e ON e.id = os.entity_id "
            "ORDER BY os.conviction_score DESC"
        ).fetchall()
        out = []
        for signal_id, name, conviction, status, detected_at, entity_id in rows:
            source_row = conn.execute(
                "SELECT source_name FROM v_data_points_with_confidence WHERE entity_id = ? "
                "ORDER BY observed_at DESC LIMIT 1",
                (entity_id,),
            ).fetchone()
            out.append(
                {
                    "id": signal_id,
                    "founder_name": name,
                    "conviction_score": conviction,
                    "status": status,
                    "detected_at": detected_at,
                    "source_channel": source_row[0] if source_row else "memory",
                }
            )
    return out


# --- memory: needs-review + entity directory -------------------------------


@app.get("/api/needs-review")
def list_needs_review():
    with db_lock:
        conn = get_conn()
        rows = conn.execute(
            "SELECT raw_record_id, source_name, raw_payload, ingested_at FROM v_needs_review"
        ).fetchall()
        out = []
        for raw_record_id, source_name, raw_payload, ingested_at in rows:
            candidates = find_candidate_entities(conn, raw_record_id)
            preview = raw_payload[:300] + ("..." if len(raw_payload) > 300 else "")
            out.append(
                {
                    "raw_record_id": raw_record_id,
                    "source_name": source_name,
                    "payload_preview": preview,
                    "candidate_entities": [
                        {"entity_id": eid, "canonical_name": name, "matched_identifier": mi}
                        for eid, name, mi in candidates
                    ],
                    "ingested_at": ingested_at,
                }
            )
    return out


class ResolveDecision(BaseModel):
    type: Literal["merge", "create_new"]
    entity_id: Optional[int] = None


@app.post("/api/needs-review/{raw_record_id}/resolve")
def resolve_needs_review(raw_record_id: int, decision: ResolveDecision):
    if decision.type == "merge" and decision.entity_id is None:
        raise HTTPException(status_code=422, detail="entity_id is required for a merge decision")

    with db_lock:
        conn = get_conn()
        try:
            py_decision = decision.entity_id if decision.type == "merge" else "new"
            entity_id = resolve_entity(conn, raw_record_id, py_decision)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

        normalize_raw_record(conn, raw_record_id)
        attribute_names = [
            r[0]
            for r in conn.execute(
                "SELECT DISTINCT attribute_name FROM data_points WHERE raw_record_id = ?",
                (raw_record_id,),
            ).fetchall()
        ]
        for attribute_name in attribute_names:
            compute_trust_scores(conn, entity_id, attribute_name)

        entity_type = conn.execute(
            "SELECT type FROM entities WHERE id = ?", (entity_id,)
        ).fetchone()[0]
        if entity_type == "founder":
            compute_founder_score(conn, entity_id)

    return {"ok": True}


@app.get("/api/founders")
def list_founders():
    with db_lock:
        conn = get_conn()
        rows = conn.execute(
            "SELECT id, canonical_name FROM entities WHERE type = 'founder' ORDER BY id"
        ).fetchall()
        return [build_founder(conn, eid, name) for eid, name in rows]


@app.get("/api/entities")
def list_entities():
    with db_lock:
        conn = get_conn()
        founders = conn.execute(
            "SELECT id, canonical_name FROM entities WHERE type = 'founder' ORDER BY id"
        ).fetchall()
        companies = conn.execute(
            "SELECT id, canonical_name FROM entities WHERE type = 'company' ORDER BY id"
        ).fetchall()
        out = [{**build_founder(conn, eid, name), "type": "founder"} for eid, name in founders]
        out += [build_company(conn, eid, name) for eid, name in companies]
    return out


# --- thesis ------------------------------------------------------------


@app.get("/api/thesis")
def get_thesis_endpoint():
    with db_lock:
        conn = get_conn()
        thesis = get_thesis(conn)
        if thesis is None:
            set_thesis(
                conn,
                sectors=DEFAULT_THESIS["sectors"],
                stage=DEFAULT_THESIS["stage"],
                geography=DEFAULT_THESIS["geography"],
                check_size_min=DEFAULT_THESIS["check_size_min"],
                check_size_max=DEFAULT_THESIS["check_size_max"],
                ownership_target_pct=DEFAULT_THESIS["ownership_target_pct"],
                risk_appetite=DEFAULT_THESIS["risk_appetite"],
            )
            thesis = get_thesis(conn)
    return thesis


class ThesisIn(BaseModel):
    sectors: list[str]
    stage: str
    geography: list[str]
    check_size_min: float
    check_size_max: float
    ownership_target_pct: float
    risk_appetite: str


@app.put("/api/thesis")
def put_thesis(body: ThesisIn):
    with db_lock:
        conn = get_conn()
        set_thesis(
            conn,
            sectors=body.sectors,
            stage=body.stage,
            geography=body.geography,
            check_size_min=body.check_size_min,
            check_size_max=body.check_size_max,
            ownership_target_pct=body.ownership_target_pct,
            risk_appetite=body.risk_appetite,
        )
        thesis = get_thesis(conn)
    return thesis


# --- founder portal (no accounts: the frontend hands back whichever
# application_id it stored client-side after a founder's own submission) ---


@app.get("/api/founder-portal")
def founder_portal(application_id: Optional[int] = None):
    if application_id is None:
        return {"founder": None, "opportunity": None}
    with db_lock:
        conn = get_conn()
        opportunity = build_opportunity(conn, application_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"founder": opportunity["founder"], "opportunity": opportunity}
