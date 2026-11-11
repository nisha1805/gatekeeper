"""Web API around the classifier.

Assessments and review decisions go through a store: Postgres when DATABASE_URL
is set (append-only audit tables), otherwise memory.

Decision support only, not legal advice.
"""
from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from classifier import (
    RULES_VERSION,
    AnnexIIIArea,
    Role,
    SystemDescription,
    classify,
)
from extractor import ExtractionError, LLMError, extract, make_llm
from questions import ANNEX_AREA_LABELS, QUESTIONS, ROLE_VALUES
from store import make_store

app = FastAPI(title="Gatekeeper compliance service", version=RULES_VERSION)

store = make_store()
llm = make_llm()


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


@app.post("/assessments", status_code=201)
def create_assessment(request: AssessmentRequest) -> dict:
    assessment = classify(request.to_system())
    return store.add(request.model_dump(mode="json"), assessment.to_dict())


@app.get("/assessments")
def list_assessments() -> list[dict]:
    return store.list()


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
def create_extraction(request: ExtractionRequest) -> dict:
    """Propose answers from a description. The proposals are not classifications:
    a person confirms them, and the written rules decide the tier."""
    if llm is None:
        raise HTTPException(status_code=503, detail="the AI step is not configured")
    try:
        return extract(request.description, llm)
    except (LLMError, ExtractionError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
