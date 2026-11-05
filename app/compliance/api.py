"""Web API around the classifier. Results are kept in memory for now (step 5.3a)
and move to an append-only Postgres table in step 5.3b.

Decision support only, not legal advice.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from classifier import (
    RULES_VERSION,
    AnnexIIIArea,
    Role,
    SystemDescription,
    classify,
)

app = FastAPI(title="Gatekeeper compliance service", version=RULES_VERSION)

# In-memory store for step 5.3a. Replaced by Postgres in 5.3b.
_STORE: list[dict] = []


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


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "rules_version": RULES_VERSION}


@app.post("/assessments", status_code=201)
def create_assessment(request: AssessmentRequest) -> dict:
    assessment = classify(request.to_system())
    record = {
        "id": str(uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "request": request.model_dump(mode="json"),
        "assessment": assessment.to_dict(),
    }
    _STORE.append(record)
    return record


@app.get("/assessments")
def list_assessments() -> list[dict]:
    return list(_STORE)


@app.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: str) -> dict:
    for record in _STORE:
        if record["id"] == assessment_id:
            return record
    raise HTTPException(status_code=404, detail="assessment not found")