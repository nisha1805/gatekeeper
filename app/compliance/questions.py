"""The question list: the single source of truth for what the service asks about a system.

The extractor prompts the AI with these questions, and GET /questions serves them to
user interfaces. A test checks that every question is a field of the assessment request.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Question:
    field: str
    kind: str  # "bool", "role" or "areas"
    group: str  # "scope", "prohibited", "high_risk" or "transparency"
    text: str


QUESTIONS: tuple[Question, ...] = (
    Question("eu_nexus", "bool", "scope", "Placed on the EU market, or its output is used in the EU"),
    Question("role", "role", "scope", "Whether the user is the provider (builds or sells the system) or the deployer (uses it)"),
    Question("manipulative_techniques", "bool", "prohibited", "Uses subliminal, manipulative or deceptive techniques that distort behaviour and could cause significant harm"),
    Question("exploits_vulnerabilities", "bool", "prohibited", "Exploits vulnerabilities linked to age, disability or social or economic situation"),
    Question("sexual_deepfakes_without_consent", "bool", "prohibited", "Generates intimate or sexually explicit images of a real person without their consent"),
    Question("child_abuse_material", "bool", "prohibited", "Generates child sexual abuse material"),
    Question("social_scoring", "bool", "prohibited", "Scores people over time from their social behaviour or traits, leading to unfavourable treatment"),
    Question("crime_prediction_by_profiling_only", "bool", "prohibited", "Predicts a person's risk of committing a crime based only on profiling"),
    Question("untargeted_face_scraping", "bool", "prohibited", "Builds facial recognition databases by scraping images from the internet or CCTV"),
    Question("emotion_inference_at_work_or_school", "bool", "prohibited", "Infers people's emotions at work or in education"),
    Question("emotion_inference_medical_or_safety_reason", "bool", "prohibited", "...and does so only for a medical or safety reason"),
    Question("biometric_categorisation_sensitive_traits", "bool", "prohibited", "Categorises people by biometrics to infer race, opinions, beliefs, sex life or orientation"),
    Question("realtime_remote_biometric_id_by_police", "bool", "prohibited", "Real-time remote biometric identification in public spaces for law enforcement"),
    Question("annex1_safety_component", "bool", "high_risk", "Is a safety component of a regulated product that needs third-party conformity assessment"),
    Question("annex3_areas", "areas", "high_risk", "Which Annex III high-risk areas the system is used in"),
    Question("performs_profiling", "bool", "high_risk", "Profiles natural persons"),
    Question("narrow_procedural_task", "bool", "high_risk", "Only performs a narrow procedural task"),
    Question("improves_prior_human_activity", "bool", "high_risk", "Only improves the result of an activity a human already completed"),
    Question("detects_patterns_without_replacing_review", "bool", "high_risk", "Only detects decision patterns and does not replace human review"),
    Question("preparatory_task", "bool", "high_risk", "Only performs a preparatory task for an assessment"),
    Question("interacts_directly_with_people", "bool", "transparency", "Interacts directly with people (for example a chatbot)"),
    Question("generates_synthetic_content", "bool", "transparency", "Generates synthetic audio, image, video or text"),
    Question("emotion_recognition_or_biometric_categorisation", "bool", "transparency", "Is an emotion recognition or biometric categorisation system"),
    Question("generates_deepfakes", "bool", "transparency", "Generates or manipulates deepfake content"),
    Question("publishes_ai_text_on_public_interest", "bool", "transparency", "Publishes AI-generated text to inform the public on matters of public interest"),
)

ANNEX_AREA_LABELS = {
    "biometrics": "Biometrics",
    "critical_infrastructure": "Critical infrastructure",
    "education": "Education and vocational training",
    "employment": "Employment and workers' management",
    "essential_services": "Essential private and public services",
    "law_enforcement": "Law enforcement",
    "migration_border": "Migration, asylum and border control",
    "justice_democracy": "Justice and democratic processes",
}

ROLE_VALUES = ("provider", "deployer")
BY_FIELD = {question.field: question for question in QUESTIONS}
PROHIBITED_FIELDS = frozenset(q.field for q in QUESTIONS if q.group == "prohibited")
