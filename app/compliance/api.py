"""Web API around the classifier.

Assessments and review decisions go through a store: Postgres when DATABASE_URL
is set (append-only audit tables), otherwise memory.

Decision support only, not legal advice.
"""
from __future__ import annotations

from typing import Literal

import hashlib
from pathlib import Path

import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from agreement import measure, summarise
from articles import sources_for
from classifier import (
    RULES_VERSION,
    AnnexIIIArea,
    Role,
    SystemDescription,
    classify,
)
from explainer import explain
from guards import RateLimiter, looks_like_instructions, mask_personal_data
from extractor import ExtractionError, LLMError, extract, make_llm
from questions import ANNEX_AREA_LABELS, QUESTIONS, ROLE_VALUES
from store import make_store

app = FastAPI(title="Gatekeeper compliance service", version=RULES_VERSION)

store = make_store()
llm = make_llm()

WEB_DIR = Path(__file__).parent / "web"

# The two endpoints that call the paid AI are limited per client and overall.
limiter = RateLimiter(
    per_client=int(os.environ.get("AI_RATE_LIMIT_PER_MINUTE", "10")),
    overall=int(os.environ.get("AI_GLOBAL_RATE_LIMIT_PER_MINUTE", "30")),
)


def _limit(request: Request) -> None:
    wait = limiter.check(request.client.host if request.client else "unknown")
    if wait is not None:
        raise HTTPException(
            status_code=429,
            detail="Too many AI requests. Please wait a moment and try again.",
            headers={"Retry-After": str(int(wait) + 1)},
        )

# The pages load only their own scripts and styles. Nothing is inlined, so a script
# injected through a description would not run even if it got into the page.
PAGE_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


@app.middleware("http")
async def add_page_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/app"):
        for name, value in PAGE_SECURITY_HEADERS.items():
            response.headers[name] = value
        if os.environ.get("DEMO_MODE") == "1":
            # The public demo is shown inside the Hugging Face Space page.
            response.headers["Content-Security-Policy"] = PAGE_SECURITY_HEADERS[
                "Content-Security-Policy"
            ].replace("frame-ancestors 'none'", "frame-ancestors https://huggingface.co https://*.huggingface.co")
    return response


@app.get("/", include_in_schema=False)
def home() -> RedirectResponse:
    return RedirectResponse("/app/")


class AssessmentRequest(BaseModel):
    """Answers about one AI system. Unknown fields are rejected on purpose: a
    misspelled field name would otherwise be ignored and give a wrong tier."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field("unnamed system", min_length=1, max_length=200)
    role: Role = Role.PROVIDER
    eu_nexus: bool = True
    manipulative_techniques: bool = False
    exploits_vulnerabilities: bool = False
    sexual_deepfakes_without_consent: bool = False
    child_abuse_material: bool = False
    social_scoring: bool = False
    crime_prediction_by_profiling_only: bool = False
    untargeted_face_scraping: bool = False
    emotion_inference_at_work_or_school: bool = False
    emotion_inference_medical_or_safety_reason: bool = False
    biometric_categorisation_sensitive_traits: bool = False
    realtime_remote_biometric_id_by_police: bool = False
    annex1_safety_component: bool = False
    annex3_areas: list[AnnexIIIArea] = []
    performs_profiling: bool = False
    narrow_procedural_task: bool = False
    improves_prior_human_activity: bool = False
    detects_patterns_without_replacing_review: bool = False
    preparatory_task: bool = False
    interacts_directly_with_people: bool = False
    generates_synthetic_content: bool = False
    emotion_recognition_or_biometric_categorisation: bool = False
    generates_deepfakes: bool = False
    publishes_ai_text_on_public_interest: bool = False

    def to_system(self) -> SystemDescription:
        data = self.model_dump()
        data["annex3_areas"] = frozenset(self.annex3_areas)
        return SystemDescription(**data)


class ExtractionRequest(BaseModel):
    """A free-text description of an AI system. Enter synthetic or public data only."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str = Field(min_length=20, max_length=4000)


class ReviewRequest(BaseModel):
    """A reviewer's decision. The reviewer name is typed, not authenticated:
    this is a prototype without login."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    decision: Literal["approved", "rejected"]
    reviewer: str = Field(min_length=1, max_length=100)
    comment: str | None = Field(None, max_length=1000)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "rules_version": RULES_VERSION}


@app.get("/config")
def config() -> dict:
    """Settings the pages need. demo: a public demo, so the pages show a notice."""
    return {"demo": os.environ.get("DEMO_MODE") == "1"}


@app.post("/assessments", status_code=201)
def create_assessment(request: AssessmentRequest, extraction_id: str | None = None) -> dict:
    """extraction_id (query parameter, optional): the AI proposals this assessment started
    from. It is kept outside the request body so the body stays exactly the question list."""
    if extraction_id is not None and store.get_extraction(extraction_id) is None:
        raise HTTPException(status_code=404, detail="extraction not found")
    assessment = classify(request.to_system())
    return store.add(request.model_dump(mode="json"), assessment.to_dict(), extraction_id)


@app.get("/assessments")
def list_assessments() -> list[dict]:
    return store.list()


@app.get("/assessments/{assessment_id}/sources")
def assessment_sources(assessment_id: str) -> dict:
    """The exact text of every article the assessment cites, copied from EUR-Lex.
    No AI is involved in this endpoint."""
    record = store.get(assessment_id)
    if record is None:
        raise HTTPException(status_code=404, detail="assessment not found")
    return sources_for(record["assessment"])


@app.get("/ai-agreement")
def ai_agreement() -> dict:
    """How often people kept the AI's proposals unchanged, over all assessments."""
    measurements = []
    for record in store.list():
        if record.get("extraction_id"):
            extraction = store.get_extraction(record["extraction_id"])
            if extraction:
                measurements.append(measure(extraction["result"], record["request"]))
    return summarise(measurements)


@app.get("/assessments/{assessment_id}/ai-agreement")
def assessment_ai_agreement(assessment_id: str) -> dict:
    record = store.get(assessment_id)
    if record is None:
        raise HTTPException(status_code=404, detail="assessment not found")
    extraction = store.get_extraction(record["extraction_id"]) if record.get("extraction_id") else None
    if extraction is None:
        return {"ai_used": False}
    return measure(extraction["result"], record["request"])


@app.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: str) -> dict:
    record = store.get(assessment_id)
    if record is None:
        raise HTTPException(status_code=404, detail="assessment not found")
    return record


@app.post("/assessments/{assessment_id}/reviews", status_code=201)
def add_review(assessment_id: str, review: ReviewRequest) -> dict:
    event = store.add_review(
        assessment_id, review.decision, review.reviewer, review.comment
    )
    if event is None:
        raise HTTPException(status_code=404, detail="assessment not found")
    return event


@app.post("/assessments/{assessment_id}/explanation")
def explain_assessment(assessment_id: str, request: Request) -> dict:
    """A plain-language explanation of a stored assessment. The AI may only use the
    articles the rules cited; if it fails or breaks that rule, a fixed template is used."""
    record = store.get(assessment_id)
    if record is None:
        raise HTTPException(status_code=404, detail="assessment not found")
    if llm is not None:
        _limit(request)
    return explain(record["assessment"], llm)


@app.get("/questions")
def list_questions() -> dict:
    """The question list, so that user interfaces do not need their own copy."""
    return {
        "questions": [
            {"field": q.field, "kind": q.kind, "group": q.group, "text": q.text}
            for q in QUESTIONS
        ],
        "annex3_areas": [
            {"value": value, "label": label} for value, label in ANNEX_AREA_LABELS.items()
        ],
        "roles": list(ROLE_VALUES),
    }


@app.post("/extractions")
def create_extraction(request: ExtractionRequest, http: Request) -> dict:
    """Propose answers from a description. The proposals are not classifications:
    a person confirms them, and the written rules decide the tier."""
    if llm is None:
        raise HTTPException(status_code=503, detail="the AI step is not configured")
    _limit(http)
    # The AI only ever sees the masked text, and the quotes are checked against it.
    masked, counts = mask_personal_data(request.description)
    suspicious = looks_like_instructions(masked)
    try:
        result = extract(masked, llm, suspicious=suspicious)
    except (LLMError, ExtractionError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    result["personal_data_masked"] = counts
    result["instruction_like_text"] = suspicious
    digest = hashlib.sha256(masked.encode("utf-8")).hexdigest()
    stored = store.add_extraction(result, digest)
    return {**result, "extraction_id": stored["id"]}


# Last, so the API routes above always win.
app.mount("/app", StaticFiles(directory=WEB_DIR, html=True), name="pages")
