
"""Deterministic LLM fallback — T2-9.

Provides deterministic templates without external API calls when the
primary LLM provider is unavailable or returns invalid output.
"""
from __future__ import annotations

import logging

from llm.output_validator import LLMOutput
from schemas.report import IssueCategory

logger = logging.getLogger(__name__)

# Human-readable category labels.
_CATEGORY_LABELS: dict[str, str] = {
    "pothole": "pothole",
    "waterlogging": "waterlogging / flooding",
    "broken_streetlight": "broken streetlight",
    "garbage_overflow": "garbage overflow",
    "open_drain": "open drain",
    "illegal_construction": "illegal construction",
    "water_supply": "water supply issue",
    "sewage": "sewage problem",
    "road_damage": "road damage",
    "other": "civic issue",
}

# Default authority for each category.
_DEFAULT_AUTHORITY: dict[str, str] = {
    "pothole": "MCC",
    "waterlogging": "MCC Drainage",
    "broken_streetlight": "MESCOM",
    "garbage_overflow": "MCC",
    "open_drain": "MCC Drainage",
    "illegal_construction": "MUDA",
    "water_supply": "MWWD",
    "sewage": "MCC Drainage",
    "road_damage": "MCC",
    "other": "MCC",
}


def _label(category: str) -> str:
    return _CATEGORY_LABELS.get(category, category)


def _authority(category: str) -> str:
    return _DEFAULT_AUTHORITY.get(category, "MCC")


# ---------------------------------------------------------------------------
# Use case 1: Complaint description
# ---------------------------------------------------------------------------

def fallback_complaint_description(
    category: str,
    address: str,
    confidence: float,
    detected_objects: str = "",
) -> LLMOutput:
    """Generate a deterministic complaint description."""
    cat_label = _label(category)

    obj_suffix = (
        f" Detected objects in the image: {detected_objects}."
        if detected_objects and category != "other"
        else ""
    )

    description = (
        f"A {cat_label} has been reported at {address}. "
        f"The evidence confidence level is {confidence:.0%}."
        f"{obj_suffix} Please inspect and take appropriate action "
        "as soon as possible."
    )[:500]

    try:
        cat_enum = IssueCategory(category)
    except ValueError:
        cat_enum = IssueCategory.other
        category = "other"

    logger.debug(
        "fallback_complaint_description: category=%s address=%s conf=%.2f",
        category, address, confidence,
    )

    return LLMOutput(
        category=cat_enum,
        description=description,
        authority_recommendation=_authority(category),
        confidence=min(max(float(confidence), 0.0), 1.0),
    )


# ---------------------------------------------------------------------------
# Use case 2: RTI draft
# ---------------------------------------------------------------------------

def fallback_rti_draft(
    category: str,
    address: str,
    submitted_at: str,
    authority_name: str,
    mock_gov_ref: str,
    status: str,
    days_elapsed: int,
) -> LLMOutput:
    """Generate a deterministic RTI draft."""
    cat_label = _label(category)

    draft = (
        f"To,\n"
        f"The Public Information Officer,\n"
        f"{authority_name},\n"
        f"Mangaluru, Karnataka.\n\n"
        f"Subject: RTI Application regarding civic complaint "
        f"(Ref: {mock_gov_ref})\n\n"
        f"I hereby request, under Section 6 of the Right to "
        f"Information Act 2005, the following information regarding "
        f"my civic complaint:\n\n"
        f"Complaint Reference: {mock_gov_ref}\n"
        f"Issue Type: {cat_label}\n"
        f"Location: {address}\n"
        f"Submitted On: {submitted_at}\n"
        f"Current Status: {status}\n"
        f"Days Elapsed Without Resolution: {days_elapsed}\n\n"
        f"Information Sought:\n"
        f"1. Current status of the complaint and actions taken.\n"
        f"2. Name and designation of the officer responsible.\n"
        f"3. Timeline of inspections and repair work (if any).\n"
        f"4. Reason for delay if unresolved after {days_elapsed} days.\n\n"
        f"I request a response within 30 days as mandated by the "
        f"RTI Act 2005.\n\n"
        f"Yours sincerely,\n[Applicant Name]\n[Contact Details]"
    )[:500]

    try:
        cat_enum = IssueCategory(category)
    except ValueError:
        cat_enum = IssueCategory.other

    logger.debug(
        "fallback_rti_draft: category=%s authority=%s days=%d",
        category, authority_name, days_elapsed,
    )

    return LLMOutput(
        category=cat_enum,
        description=draft,
        authority_recommendation=authority_name or _authority(category),
        confidence=0.7,
    )


# ---------------------------------------------------------------------------
# Use case 3: Category classification from objects and address
# ---------------------------------------------------------------------------

def fallback_classify_category(
    detected_objects: str,
    address: str,
) -> LLMOutput:
    """Classify an issue using conservative keyword matching."""
    obj_lower = detected_objects.lower()
    addr_lower = address.lower()

    # Ordinary vehicles are deliberately NOT treated as road damage.
    # A vehicle in an image does not establish that a road is damaged.
    _OBJ_KEYWORD_MAP: list[tuple[str, IssueCategory]] = [
        ("pothole", IssueCategory.pothole),
        ("garbage", IssueCategory.garbage_overflow),
        ("trash", IssueCategory.garbage_overflow),
        ("rubbish", IssueCategory.garbage_overflow),
        ("litter", IssueCategory.garbage_overflow),
        ("waste", IssueCategory.garbage_overflow),
        ("bottle", IssueCategory.garbage_overflow),
        ("cup", IssueCategory.garbage_overflow),
        ("banana", IssueCategory.garbage_overflow),
        ("food waste", IssueCategory.garbage_overflow),
        ("suitcase", IssueCategory.garbage_overflow),
        ("toilet", IssueCategory.sewage),
        ("sink", IssueCategory.water_supply),
        ("boat", IssueCategory.waterlogging),
        ("traffic light", IssueCategory.broken_streetlight),
        ("fire hydrant", IssueCategory.broken_streetlight),
    ]

    _ADDR_KEYWORD_MAP: list[tuple[str, IssueCategory]] = [
        ("pothole", IssueCategory.pothole),
        ("pot hole", IssueCategory.pothole),
        ("waterlog", IssueCategory.waterlogging),
        ("flood", IssueCategory.waterlogging),
        ("open drain", IssueCategory.open_drain),
        ("drain", IssueCategory.open_drain),
        ("sewage", IssueCategory.sewage),
        ("sewer", IssueCategory.sewage),
        ("streetlight", IssueCategory.broken_streetlight),
        ("street light", IssueCategory.broken_streetlight),
        ("lamp", IssueCategory.broken_streetlight),
        ("garbage", IssueCategory.garbage_overflow),
        ("rubbish", IssueCategory.garbage_overflow),
        ("waste", IssueCategory.garbage_overflow),
        ("litter", IssueCategory.garbage_overflow),
        ("water supply", IssueCategory.water_supply),
        ("water pipe", IssueCategory.water_supply),
        ("road damage", IssueCategory.road_damage),
        ("damaged road", IssueCategory.road_damage),
        ("broken road", IssueCategory.road_damage),
        ("construction", IssueCategory.illegal_construction),
        ("encroachment", IssueCategory.illegal_construction),
    ]

    matched_category = IssueCategory.other
    match_source = "none"

    for keyword, cat in _OBJ_KEYWORD_MAP:
        if keyword in obj_lower:
            matched_category = cat
            match_source = "objects"
            break

    if matched_category is IssueCategory.other:
        for keyword, cat in _ADDR_KEYWORD_MAP:
            if keyword in addr_lower:
                matched_category = cat
                match_source = "address"
                break

    cat_value = matched_category.value
    description = (
        f"Based on detected objects ({detected_objects or 'none'}) "
        f"at {address}, this appears to be a {_label(cat_value)} issue."
    )[:500]

    logger.debug(
        "fallback_classify_category: objects=%r address=%r "
        "category=%s source=%s",
        detected_objects, address, cat_value, match_source,
    )

    return LLMOutput(
        category=matched_category,
        description=description,
        authority_recommendation=_authority(cat_value),
        confidence=0.5,
    )


# ---------------------------------------------------------------------------
# Use case 4: Vision category mapping
# ---------------------------------------------------------------------------

_VISION_CATEGORY_MAP: dict[str, IssueCategory] = {
    "pothole": IssueCategory.pothole,
    "road_damage": IssueCategory.road_damage,
    "broken_streetlight": IssueCategory.broken_streetlight,
    "garbage_overflow": IssueCategory.garbage_overflow,
    "open_drain": IssueCategory.open_drain,
    "illegal_construction": IssueCategory.illegal_construction,
    "waterlogging": IssueCategory.waterlogging,
    "water_supply": IssueCategory.water_supply,
    "sewage": IssueCategory.sewage,
    "other": IssueCategory.other,
    "invalid": IssueCategory.other,
    "water_sewage": IssueCategory.water_supply,
    "streetlight": IssueCategory.broken_streetlight,
    "garbage": IssueCategory.garbage_overflow,
    "rubbish": IssueCategory.garbage_overflow,
    "litter": IssueCategory.garbage_overflow,
    "waste": IssueCategory.garbage_overflow,
    "electrical": IssueCategory.broken_streetlight,
    "drainage": IssueCategory.open_drain,
    "water_leakage": IssueCategory.water_supply,
    "broken_road_marking": IssueCategory.road_damage,
    "other_civic": IssueCategory.other,
}

_WATER_SEWAGE_REASON_MAP: dict[str, IssueCategory] = {
    "water_leakage": IssueCategory.water_supply,
    "water leakage": IssueCategory.water_supply,
    "leaking pipe": IssueCategory.water_supply,
    "pipe": IssueCategory.water_supply,
    "burst": IssueCategory.water_supply,
    "sewage": IssueCategory.sewage,
    "sewer": IssueCategory.sewage,
    "wastewater": IssueCategory.sewage,
    "waterlogging": IssueCategory.waterlogging,
    "flooding": IssueCategory.waterlogging,
    "standing water": IssueCategory.waterlogging,
    "flood": IssueCategory.waterlogging,
}


def _map_water_sewage_reason(reason: str) -> IssueCategory:
    """Resolve a water/sewage category to its most specific subtype."""
    reason_lower = reason.strip().lower()

    for keyword, category in _WATER_SEWAGE_REASON_MAP.items():
        if keyword in reason_lower:
            return category

    return IssueCategory.water_supply


def map_vision_category_to_issue_category(
    vision_cat: str,
    reason: str = "",
) -> IssueCategory:
    """Map a vision-model category to the application's category enum."""
    try:
        from llm.groq_provider import _normalise_category
        key = _normalise_category(vision_cat)
    except Exception:
        key = vision_cat.strip().lower()

    if key == "water_sewage":
        return _map_water_sewage_reason(reason)

    try:
        return IssueCategory(key)
    except ValueError:
        return _VISION_CATEGORY_MAP.get(key, IssueCategory.other)


# ---------------------------------------------------------------------------
# Heuristic civic image classifier — used when Groq vision fails
# ---------------------------------------------------------------------------

def fallback_civic_classify_image(
    yolo_class: str,
    all_class_names: tuple,
    address: str,
) -> "CivicClassificationResult":
    """Classify an image conservatively when the vision API is unavailable."""
    from llm.groq_provider import CivicClassificationResult

    obj_str = " ".join(
        str(name).lower() for name in all_class_names
    ) + " " + yolo_class.lower()

    addr_lower = address.lower()

    # Never infer road damage merely from cars, trucks, bikes, buses,
    # traffic lights, or stop signs. They may appear in unrelated images.
    _OBJ_KEYWORD_MAP: list[tuple[str, str, str, float]] = [
        ("garbage", "garbage", "medium", 0.5),
        ("rubbish", "garbage", "medium", 0.5),
        ("trash", "garbage", "medium", 0.5),
        ("litter", "garbage", "medium", 0.5),
        ("waste", "garbage", "medium", 0.5),
        ("bottle", "garbage", "medium", 0.5),
        ("cup", "garbage", "medium", 0.5),
        ("bowl", "garbage", "medium", 0.5),
        ("toilet", "sewage", "high", 0.85),
        ("sink", "water_leakage", "medium", 0.5),
        ("boat", "waterlogging", "high", 0.85),
        ("pothole", "pothole", "medium", 0.5),
        ("open drain", "open_drain", "medium", 0.5),
    ]

    matched_cat = None
    matched_severity = "low"
    matched_sev_score = 0.3

    for keyword, vision_cat, severity, severity_score in _OBJ_KEYWORD_MAP:
        if keyword in obj_str:
            matched_cat = vision_cat
            matched_severity = severity
            matched_sev_score = severity_score
            break

    if matched_cat is None:
        _ADDR_KEYWORD_MAP: list[tuple[str, str, str, float]] = [
            ("pothole", "pothole", "medium", 0.5),
            ("pot hole", "pothole", "medium", 0.5),
            ("waterlog", "waterlogging", "high", 0.85),
            ("flood", "waterlogging", "high", 0.85),
            ("open drain", "open_drain", "medium", 0.5),
            ("drain", "open_drain", "medium", 0.5),
            ("sewage", "sewage", "high", 0.85),
            ("sewer", "sewage", "high", 0.85),
            ("streetlight", "streetlight", "medium", 0.5),
            ("street light", "streetlight", "medium", 0.5),
            ("garbage", "garbage", "medium", 0.5),
            ("rubbish", "garbage", "medium", 0.5),
            ("trash", "garbage", "medium", 0.5),
            ("waste", "garbage", "medium", 0.5),
            ("litter", "garbage", "medium", 0.5),
            ("water pipe", "water_leakage", "medium", 0.5),
            ("water supply", "water_leakage", "medium", 0.5),
            ("encroach", "illegal_construction", "medium", 0.5),
            ("illegal construction", "illegal_construction", "medium", 0.5),
            ("construction", "illegal_construction", "low", 0.3),
            ("road damage", "road_damage", "medium", 0.5),
            ("damaged road", "road_damage", "medium", 0.5),
            ("broken road", "road_damage", "medium", 0.5),
        ]

        for keyword, vision_cat, severity, severity_score in _ADDR_KEYWORD_MAP:
            if keyword in addr_lower:
                matched_cat = vision_cat
                matched_severity = severity
                matched_sev_score = severity_score
                break

    if matched_cat is None:
        matched_cat = "other"
        matched_severity = "low"
        matched_sev_score = 0.2

    description = (
        f"A potential "
        f"{_label(map_vision_category_to_issue_category(matched_cat).value)} "
        f"issue has been reported at {address}. "
        "Please inspect and take appropriate action."
    )[:500]

    logger.debug(
        "fallback_civic_classify_image: yolo=%r address=%r category=%s",
        yolo_class, address, matched_cat,
    )

    return CivicClassificationResult(
        valid=True,
        category=matched_cat,
        category_confidence=0.45,
        severity=matched_severity,
        severity_score=matched_sev_score,
        description=description,
        reason="heuristic_fallback",
    )
