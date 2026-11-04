"""EU AI Act risk classification as plain, testable rules.

Decision support only, not legal advice. The rules follow Regulation (EU) 2024/1689
as amended by Regulation (EU) 2026/1744. The law was read on a third-party reference
site and has not yet been checked line by line against EUR-Lex.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

RULES_VERSION = "0.1.0"
DISCLAIMER = "Decision support only, not legal advice."
SOURCE_NOTE = (
    "Rules follow Regulation (EU) 2024/1689 as amended by Regulation (EU) 2026/1744. "
    "The text was read on a third-party reference site and is not yet checked "
    "line by line against EUR-Lex."
)


class Role(str, Enum):
    PROVIDER = "provider"
    DEPLOYER = "deployer"


class Tier(str, Enum):
    OUT_OF_SCOPE = "out_of_scope"
    PROHIBITED = "prohibited"
    HIGH_RISK = "high_risk"
    LIMITED_RISK = "limited_risk"  # transparency duties only
    MINIMAL_RISK = "minimal_risk"


class AnnexIIIArea(str, Enum):
    BIOMETRICS = "biometrics"
    CRITICAL_INFRASTRUCTURE = "critical_infrastructure"
    EDUCATION = "education"
    EMPLOYMENT = "employment"
    ESSENTIAL_SERVICES = "essential_services"
    LAW_ENFORCEMENT = "law_enforcement"
    MIGRATION_BORDER = "migration_border"
    JUSTICE_DEMOCRACY = "justice_democracy"


ANNEX_III_POINT = {
    AnnexIIIArea.BIOMETRICS: 1,
    AnnexIIIArea.CRITICAL_INFRASTRUCTURE: 2,
    AnnexIIIArea.EDUCATION: 3,
    AnnexIIIArea.EMPLOYMENT: 4,
    AnnexIIIArea.ESSENTIAL_SERVICES: 5,
    AnnexIIIArea.LAW_ENFORCEMENT: 6,
    AnnexIIIArea.MIGRATION_BORDER: 7,
    AnnexIIIArea.JUSTICE_DEMOCRACY: 8,
}


@dataclass(frozen=True)
class SystemDescription:
    """Answers about one AI system. Every yes/no answer defaults to no."""

    name: str = "unnamed system"
    role: Role = Role.PROVIDER
    eu_nexus: bool = True  # placed on the EU market, or output used in the EU (Art. 2)
    # Article 5(1): prohibited practices
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
    # Article 6 and Annex III: high-risk
    annex1_safety_component: bool = False
    annex3_areas: frozenset[AnnexIIIArea] = frozenset()
    performs_profiling: bool = False
    narrow_procedural_task: bool = False
    improves_prior_human_activity: bool = False
    detects_patterns_without_replacing_review: bool = False
    preparatory_task: bool = False
    # Article 50: transparency
    interacts_directly_with_people: bool = False
    generates_synthetic_content: bool = False
    emotion_recognition_or_biometric_categorisation: bool = False
    generates_deepfakes: bool = False
    publishes_ai_text_on_public_interest: bool = False


@dataclass(frozen=True)
class Reason:
    article: str
    text: str


@dataclass(frozen=True)
class Assessment:
    system_name: str
    role: Role
    tier: Tier
    reasons: tuple[Reason, ...]
    transparency_duties: tuple[Reason, ...]
    notes: tuple[str, ...]
    rules_version: str = RULES_VERSION
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict:
        """A plain dictionary that can be stored or sent as JSON."""
        return {
            "system_name": self.system_name,
            "role": self.role.value,
            "tier": self.tier.value,
            "reasons": [{"article": r.article, "text": r.text} for r in self.reasons],
            "transparency_duties": [
                {"article": r.article, "text": r.text} for r in self.transparency_duties
            ],
            "notes": list(self.notes),
            "rules_version": self.rules_version,
            "disclaimer": self.disclaimer,
        }


_PROHIBITED = (
    ("manipulative_techniques", "Art. 5(1)(a)",
     "Subliminal, manipulative or deceptive techniques that materially distort behaviour and are likely to cause significant harm."),
    ("exploits_vulnerabilities", "Art. 5(1)(b)",
     "Exploiting vulnerabilities linked to age, disability or social or economic situation in a way likely to cause significant harm."),
    ("sexual_deepfakes_without_consent", "Art. 5(1)(ba)",
     "Generating or manipulating realistic intimate or sexually explicit material of an identifiable person without their consent."),
    ("child_abuse_material", "Art. 5(1)(bb)",
     "Generating or manipulating child sexual abuse material."),
    ("social_scoring", "Art. 5(1)(c)",
     "Social scoring of people over time that leads to unjustified or out-of-context unfavourable treatment."),
    ("crime_prediction_by_profiling_only", "Art. 5(1)(d)",
     "Predicting that a person will commit a crime based solely on profiling or personality traits."),
    ("untargeted_face_scraping", "Art. 5(1)(e)",
     "Building or expanding facial recognition databases by untargeted scraping of internet or CCTV images."),
    ("biometric_categorisation_sensitive_traits", "Art. 5(1)(g)",
     "Biometric categorisation that infers race, political opinions, trade union membership, beliefs, sex life or sexual orientation."),
    ("realtime_remote_biometric_id_by_police", "Art. 5(1)(h)",
     "Real-time remote biometric identification in public spaces for law enforcement, outside the narrow listed exceptions."),
)

_TRANSPARENCY = (
    ("interacts_directly_with_people", "Art. 50(1)",
     "People must be told they are interacting with an AI system, unless that is obvious."),
    ("generates_synthetic_content", "Art. 50(2)",
     "Synthetic audio, image, video or text outputs must be marked in a machine-readable way."),
    ("emotion_recognition_or_biometric_categorisation", "Art. 50(3)",
     "Deployers must inform people exposed to emotion recognition or biometric categorisation."),
    ("generates_deepfakes", "Art. 50(4)",
     "Deepfake content must be disclosed as artificially generated or manipulated."),
    ("publishes_ai_text_on_public_interest", "Art. 50(4)",
     "AI-generated text published to inform the public on matters of public interest must be disclosed, unless it was human-reviewed under editorial responsibility."),
)


def _prohibited(system: SystemDescription) -> tuple[list[Reason], list[str]]:
    reasons = [
        Reason(article, text)
        for field_name, article, text in _PROHIBITED
        if getattr(system, field_name)
    ]
    notes: list[str] = []
    if system.emotion_inference_at_work_or_school:
        if system.emotion_inference_medical_or_safety_reason:
            notes.append(
                "Art. 5(1)(f): a medical or safety reason was claimed for emotion inference "
                "at work or school. Check that the exception really applies."
            )
        else:
            reasons.append(Reason(
                "Art. 5(1)(f)",
                "Inferring emotions in the workplace or in education, except for medical or safety reasons.",
            ))
    if any(r.article in ("Art. 5(1)(ba)", "Art. 5(1)(bb)") for r in reasons):
        notes.append(
            "The bans in Art. 5(1)(ba) and (bb) were added in 2026. One source says they apply "
            "from 2 December 2026. Verify the date in Art. 113 on EUR-Lex."
        )
    if any(r.article == "Art. 5(1)(h)" for r in reasons):
        notes.append(
            "Art. 5(1)(h) allows narrow law-enforcement exceptions with prior authorisation. "
            "Seek legal advice."
        )
    return reasons, notes


def _high_risk(system: SystemDescription) -> tuple[list[Reason], list[str]]:
    reasons: list[Reason] = []
    notes: list[str] = []
    if system.annex1_safety_component:
        reasons.append(Reason(
            "Art. 6(1)",
            "The system is a safety component of, or is itself, a product under the Annex I "
            "harmonisation legislation that needs third-party conformity assessment.",
        ))
        notes.append(
            "High-risk obligations for AI in regulated products (Annex I) apply from "
            "2 August 2028 (Regulation (EU) 2026/1744). Verify on EUR-Lex."
        )
    exception_available = (
        system.narrow_procedural_task
        or system.improves_prior_human_activity
        or system.detects_patterns_without_replacing_review
        or system.preparatory_task
    )
    annex3_hit = False
    for area in sorted(system.annex3_areas, key=lambda a: ANNEX_III_POINT[a]):
        point = ANNEX_III_POINT[area]
        label = area.value.replace("_", " ")
        if system.performs_profiling:
            reasons.append(Reason(
                f"Art. 6(3), Annex III point {point}",
                f"The use case falls in Annex III point {point} ({label}) and the system profiles "
                "natural persons, so the Art. 6(3) exception never applies.",
            ))
            annex3_hit = True
        elif exception_available:
            notes.append(
                f"Annex III point {point} ({label}): an Art. 6(3) exception was reported, so this "
                "tool does not rate the system high-risk. Art. 6(4): a provider relying on it must "
                "document the assessment before placing the system on the market and register it "
                "(Art. 49(2)). This tool cannot make that judgement."
            )
        else:
            reasons.append(Reason(
                f"Art. 6(2), Annex III point {point}",
                f"The use case falls in Annex III point {point} ({label}).",
            ))
            annex3_hit = True
    if annex3_hit:
        notes.append(
            "High-risk obligations for stand-alone systems (Annex III) apply from "
            "2 December 2027 (Regulation (EU) 2026/1744). Verify on EUR-Lex."
        )
    return reasons, notes


def _transparency(system: SystemDescription) -> list[Reason]:
    return [
        Reason(article, text)
        for field_name, article, text in _TRANSPARENCY
        if getattr(system, field_name)
    ]


def _assessment(system, tier, reasons, duties, notes) -> Assessment:
    return Assessment(
        system_name=system.name,
        role=system.role,
        tier=tier,
        reasons=tuple(reasons),
        transparency_duties=tuple(duties),
        notes=tuple(list(notes) + [SOURCE_NOTE]),
    )


def classify(system: SystemDescription) -> Assessment:
    """Apply the rules in a fixed order: scope, prohibited, high-risk, transparency."""
    if not system.eu_nexus:
        return _assessment(
            system, Tier.OUT_OF_SCOPE,
            [Reason("Art. 2", "The system is not placed on the EU market and its output is not used in the EU.")],
            [],
            ["The scope rule is simplified and Art. 2 has not been read in detail. Exemptions such as military or research use are not modelled."],
        )
    prohibited, notes = _prohibited(system)
    if prohibited:
        return _assessment(system, Tier.PROHIBITED, prohibited, [], notes)

    high, high_notes = _high_risk(system)
    notes = notes + high_notes
    duties = _transparency(system)
    if high:
        return _assessment(system, Tier.HIGH_RISK, high, duties, notes)
    if duties:
        return _assessment(system, Tier.LIMITED_RISK, duties, duties, notes)
    return _assessment(
        system, Tier.MINIMAL_RISK,
        [Reason("Art. 5, 6, 50", "No prohibited practice, high-risk use or transparency trigger was reported.")],
        [],
        notes,
    )