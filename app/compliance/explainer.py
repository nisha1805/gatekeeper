"""The explanation step: a short plain-language explanation of a finished assessment.

The rules have already decided the tier. The AI only rewrites the cited reasons in
plain words. The code then checks the text: it must not name any article, paragraph
or annex point that the rules did not cite, and it must not state years. If the AI
fails or breaks a rule, a fixed template built from the same reasons is used instead,
so the person always gets an explanation that is safe.
"""
from __future__ import annotations

import re

from extractor import LLMError

MAX_LENGTH = 1200

SYSTEM_PROMPT = """You explain the result of an EU AI Act risk check to a non-lawyer.

Rules:
- The risk tier and the cited reasons below were decided by written rules. Do not question or change them.
- Explain in 2 to 4 short sentences, in plain English, why the system got this tier.
- Mention only the articles listed under "Cited reasons". Never name any other article, paragraph, annex or point.
- Do not state dates or years, and do not give legal advice.
- Do not add facts about the system. You are not told its name or details on purpose.
- Reply with the explanation text only."""

_TIER_LABELS = {
    "out_of_scope": "outside the scope of the AI Act",
    "prohibited": "prohibited",
    "high_risk": "high-risk",
    "limited_risk": "limited-risk (transparency duties)",
    "minimal_risk": "minimal-risk",
}

_DESIGNATOR = r"\d+(?:\([a-z0-9]+\))*"
_ARTICLE_MENTION = re.compile(
    rf"\bArt(?:icles?|s?\.)\s*({_DESIGNATOR}(?:\s*(?:,|and|or|&|/)\s*{_DESIGNATOR})*)",
    re.IGNORECASE,
)
_DESIGNATOR_RE = re.compile(_DESIGNATOR)
_ANNEX_MENTION = re.compile(r"\bAnnex(?:es)?\s+([IVX]+)(?:\s+point\s+(\d+))?", re.IGNORECASE)
_BARE_POINT = re.compile(r"\bpoint\s+(\d+)", re.IGNORECASE)
_YEAR = re.compile(r"\b(?:19|20)\d\d\b")


def _norm(designator: str) -> str:
    return designator.lower().replace(" ", "")


def _cited_items(assessment: dict) -> list[dict]:
    """The reasons and duties the rules cited, without duplicates, in order."""
    seen, items = set(), []
    for item in list(assessment.get("reasons", [])) + list(assessment.get("transparency_duties", [])):
        key = (item["article"], item["text"])
        if key not in seen:
            seen.add(key)
            items.append(item)
    return items


def _allowed(items: list[dict]) -> tuple[set[str], set[str], set[str], set[str]]:
    """Designators (e.g. '6(3)'), bare article numbers, annex numerals, annex points."""
    designators: set[str] = set()
    numbers: set[str] = set()
    annexes: set[str] = set()
    points: set[str] = set()
    for item in items:
        article = item["article"]
        # only the part before "Annex": "Art. 6(3), Annex III point 4" cites article 6(3), not 4
        # lists such as "Art. 5, 6, 50" cite each number
        for designator in _DESIGNATOR_RE.findall(re.split(r"Annex", article)[0]):
            designators.add(_norm(designator))
            numbers.add(re.match(r"\d+", designator).group())
        for annex in _ANNEX_MENTION.finditer(article + " " + item["text"]):
            annexes.add(annex.group(1).upper())
            if annex.group(2):
                points.add(annex.group(2))
        for point in _BARE_POINT.findall(article + " " + item["text"]):
            points.add(point)
    return designators, numbers, annexes, points


def problems_in(text: str, items: list[dict]) -> list[str]:
    """Why an AI-written explanation must be rejected. Empty list means it passes."""
    problems: list[str] = []
    cleaned = (text or "").strip()
    if not cleaned:
        return ["empty explanation"]
    if len(cleaned) > MAX_LENGTH:
        problems.append("explanation is too long")
    designators, numbers, annexes, points = _allowed(items)
    mentioned = 0
    for mention in _ARTICLE_MENTION.finditer(cleaned):
        for designator in _DESIGNATOR_RE.findall(mention.group(1)):
            mentioned += 1
            wanted = _norm(designator)
            number = re.match(r"\d+", wanted).group()
            if wanted in designators:
                continue
            if wanted == number and number in numbers:
                continue  # names the whole article that was cited in part
            problems.append(f"names an article that was not cited: {designator}")
    for annex in _ANNEX_MENTION.finditer(cleaned):
        if annex.group(1).upper() not in annexes:
            problems.append(f"names an annex that was not cited: {annex.group(1)}")
        if annex.group(2) and annex.group(2) not in points:
            problems.append(f"names an annex point that was not cited: {annex.group(2)}")
    for point in _BARE_POINT.findall(cleaned):
        if point not in points:
            problems.append(f"names a point that was not cited: {point}")
    if _YEAR.search(cleaned):
        problems.append("states a year")
    if mentioned == 0:
        problems.append("does not name any cited article")
    return list(dict.fromkeys(problems))


def build_prompt(assessment: dict, items: list[dict]) -> str:
    label = _TIER_LABELS.get(assessment["tier"], assessment["tier"])
    lines = [f"Risk tier decided by the rules: {label}", "", "Cited reasons:"]
    for item in items:
        lines.append(f"- {item['article']}: {item['text']}")
    return "\n".join(lines)


def template_explanation(assessment: dict, items: list[dict]) -> str:
    """A fixed explanation built only from the rules' own text."""
    label = _TIER_LABELS.get(assessment["tier"], assessment["tier"])
    parts = [f"The rules rate this system as {label}."]
    for item in items:
        parts.append(f"{item['article']}: {item['text']}")
    return " ".join(parts)


def explain(assessment: dict, llm) -> dict:
    """Explain a stored assessment. Never raises: falls back to the template."""
    items = _cited_items(assessment)
    fallback = template_explanation(assessment, items)
    base = {"cited_articles": [item["article"] for item in items]}
    if llm is None:
        return {**base, "text": fallback, "source": "template",
                "fallback_reason": "the AI step is not configured"}
    try:
        reply = llm.complete(SYSTEM_PROMPT, build_prompt(assessment, items))
    except LLMError as error:
        return {**base, "text": fallback, "source": "template",
                "fallback_reason": f"the AI step failed: {error}"}
    problems = problems_in(reply, items)
    if problems:
        return {**base, "text": fallback, "source": "template",
                "fallback_reason": "the AI text was rejected: " + "; ".join(problems)}
    return {**base, "text": reply.strip(), "source": "ai", "model": getattr(llm, "model", None),
            "fallback_reason": None}
