"""Questionnaire and payload building for the Streamlit UI.

No classification happens here: the API decides. The UI only collects answers.
"""
from __future__ import annotations

import copy

PROHIBITED = [
    ("manipulative_techniques", "Uses subliminal, manipulative or deceptive techniques that distort behaviour and could cause significant harm"),
    ("exploits_vulnerabilities", "Exploits vulnerabilities linked to age, disability or social or economic situation"),
    ("sexual_deepfakes_without_consent", "Generates intimate or sexually explicit images of a real person without their consent"),
    ("child_abuse_material", "Generates child sexual abuse material"),
    ("social_scoring", "Scores people over time from their social behaviour or traits, leading to unfavourable treatment"),
    ("crime_prediction_by_profiling_only", "Predicts a person's risk of committing a crime based only on profiling"),
    ("untargeted_face_scraping", "Builds facial recognition databases by scraping images from the internet or CCTV"),
    ("emotion_inference_at_work_or_school", "Infers people's emotions at work or in education"),
    ("emotion_inference_medical_or_safety_reason", "...and does so only for a medical or safety reason"),
    ("biometric_categorisation_sensitive_traits", "Categorises people by biometrics to infer race, opinions, beliefs, sex life or orientation"),
    ("realtime_remote_biometric_id_by_police", "Real-time remote biometric identification in public spaces for law enforcement"),
]

HIGH_RISK = [
    ("annex1_safety_component", "Is a safety component of a regulated product that needs third-party conformity assessment"),
    ("performs_profiling", "Profiles natural persons"),
    ("narrow_procedural_task", "Only performs a narrow procedural task"),
    ("improves_prior_human_activity", "Only improves the result of an activity a human already completed"),
    ("detects_patterns_without_replacing_review", "Only detects decision patterns and does not replace human review"),
    ("preparatory_task", "Only performs a preparatory task for an assessment"),
]

TRANSPARENCY = [
    ("interacts_directly_with_people", "Interacts directly with people (for example a chatbot)"),
    ("generates_synthetic_content", "Generates synthetic audio, image, video or text"),
    ("emotion_recognition_or_biometric_categorisation", "Is an emotion recognition or biometric categorisation system"),
    ("generates_deepfakes", "Generates or manipulates deepfake content"),
    ("publishes_ai_text_on_public_interest", "Publishes AI-generated text to inform the public on matters of public interest"),
]

BOOLEAN_FIELDS = PROHIBITED + HIGH_RISK + TRANSPARENCY

ANNEX_AREAS = {
    "biometrics": "1. Biometrics",
    "critical_infrastructure": "2. Critical infrastructure",
    "education": "3. Education and vocational training",
    "employment": "4. Employment and workers' management",
    "essential_services": "5. Essential private and public services",
    "law_enforcement": "6. Law enforcement",
    "migration_border": "7. Migration, asylum and border control",
    "justice_democracy": "8. Justice and democratic processes",
}

ROLES = {
    "provider": "Provider (builds or sells the system)",
    "deployer": "Deployer (uses the system)",
}

DEFAULTS = {
    "name": "",
    "role": "provider",
    "eu_nexus": True,
    "annex3_areas": [],
    **{field: False for field, _ in BOOLEAN_FIELDS},
}

SAMPLES = {
    "Support chatbot": {"name": "Support chatbot", "interacts_directly_with_people": True},
    "CV screening": {"name": "CV screening tool", "annex3_areas": ["employment"]},
    "Spam filter": {"name": "Email spam filter"},
    "Social scoring app": {"name": "Citizen scoring app", "social_scoring": True},
}

# label, background, text colour
TIER_STYLE = {
    "prohibited": ("Prohibited", "#FDE8E8", "#A11D1D"),
    "high_risk": ("High risk", "#FFF0E0", "#8A4200"),
    "limited_risk": ("Limited risk", "#E8EEFF", "#2340B8"),
    "minimal_risk": ("Minimal risk", "#E6F4EA", "#1B6B34"),
    "out_of_scope": ("Out of scope", "#F0F2F5", "#3B4656"),
}


def sample_values(label: str) -> dict:
    """All answers for one sample, as fresh copies."""
    values = copy.deepcopy(DEFAULTS)
    values.update(copy.deepcopy(SAMPLES[label]))
    return values


def build_payload(values) -> dict:
    """The JSON the API expects. Only 'yes' answers are sent."""
    payload = {
        "name": (values.get("name") or "").strip() or "unnamed system",
        "role": values.get("role", "provider"),
        "eu_nexus": bool(values.get("eu_nexus", True)),
        "annex3_areas": list(values.get("annex3_areas", [])),
    }
    for field, _ in BOOLEAN_FIELDS:
        if values.get(field):
            payload[field] = True
    return payload