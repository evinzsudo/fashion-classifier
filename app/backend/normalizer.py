"""
Normalize AI-generated attribute values before storage to reduce filter clutter.

Rules are ordered most-specific first. If no rule matches and the value contains
a compound 'X and/or Y', the primary (first) term is kept.
"""
import re
from typing import Optional


def _match(value: str, rules: list[tuple[str, str]]) -> Optional[str]:
    v = value.lower().strip()
    for pattern, replacement in rules:
        if re.search(pattern, v, re.IGNORECASE):
            return replacement
    return None


def _take_first(value: str) -> str:
    parts = re.split(r"\s+(?:and|or|/|&)\s+", value.strip(), maxsplit=1)
    return parts[0].strip()


# ── Material ─────────────────────────────────────────────────────────────────

_MATERIAL_MODIFIERS = re.compile(
    r"^(?:\d+\s*%\s*|lightweight\s+|heavy\s+|pure\s+|stretch\s+|"
    r"woven\s+|thick\s+|thin\s+|fine\s+|soft\s+|structured\s+|knit(?:ted)?\s+)",
    re.IGNORECASE,
)

_MATERIAL_RULES: list[tuple[str, str]] = [
    # Specific compound patterns (more specific → less specific)
    (r"cotton[\s+](?:and[\s+])?polyester|polyester[\s+](?:and[\s+])?cotton|"
     r"cotton[\s/]polyester|poly(?:ester)?[\s/]cotton", "cotton blend"),
    (r"knit(?:ted)?\s+cotton(?:\s+blend)?|cotton\s+knit", "cotton blend"),
    (r"cotton\s+blend|blended\s+cotton", "cotton blend"),
    (r"knit(?:ted)?\s+wool|wool\s+knit", "wool"),
    (r"wool\s*[\s-]blend", "wool"),
    (r"canvas\s*(?:or|and|/)\s*leather|leather\s*(?:or|and|/)\s*canvas", "canvas"),
    (r"faux\s+leather|vegan\s+leather|pu\s+leather", "synthetic leather"),
    (r"synthetic\s+leather", "synthetic leather"),
    (r"stretch\s+denim|denim\s+blend", "denim"),
    (r"polyester\s+blend|blended\s+polyester", "polyester"),
    (r"linen\s+blend|blended\s+linen", "linen"),
    (r"silk\s+blend|blended\s+silk", "silk"),
    (r"nylon\s+blend|blended\s+nylon", "nylon"),
]


def normalize_material(value: str) -> str:
    if not value:
        return value
    result = _match(value, _MATERIAL_RULES)
    if result:
        return result
    v = _MATERIAL_MODIFIERS.sub("", value.lower().strip()).strip()
    if re.search(r"\s+(?:and|or|/|&)\s+", v):
        v = _take_first(v)
    return v or value.strip()


# ── Style ─────────────────────────────────────────────────────────────────────

_STYLE_RULES: list[tuple[str, str]] = [
    (r"smart\s+casual|neat\s+casual|polished\s+casual", "business casual"),
    (r"semi[\s-]formal", "business casual"),
    (r"activewear|sportswear|athleisure", "athletic"),
    (r"street\s*wear", "streetwear"),
    (r"boho(?:hemian)?", "bohemian"),
    (r"avant[\s-]garde|experimental\s+fashion", "avant-garde"),
    (r"old[\s-]money|quiet\s+luxury|clean\s+girl", "minimalist"),
]


def normalize_style(value: str) -> str:
    if not value:
        return value
    result = _match(value, _STYLE_RULES)
    if result:
        return result
    v = value.lower().strip()
    if re.search(r"\s+(?:and|or|/|&)\s+", v):
        v = _take_first(v)
    return v


# ── Occasion ──────────────────────────────────────────────────────────────────

_OCCASION_RULES: list[tuple[str, str]] = [
    (r"everyday\s+(?:casual\s+)?wear|daily\s+wear|everyday\s+use|"
     r"casual\s+daily|day[\s-]to[\s-]day", "casual everyday"),
    (r"office\s+wear|work\s+wear|work\s+outfit|nine[\s-]to[\s-]five", "business casual"),
    (r"gym|workout|fitness\s+(?:class|session)|exercise|training", "athletic"),
    (r"black[\s-]tie|gala|cocktail\s+(?:party|event)|evening\s+gown|"
     r"red\s+carpet|formal\s+(?:dinner|occasion|event|wear)", "formal event"),
    (r"beach\s+(?:wear|day|outing)|resort\s+wear|poolside", "beach"),
    (r"outdoor\s+(?:activity|adventure|recreation)|camping|hiking", "outdoor/adventure"),
]


def normalize_occasion(value: str) -> str:
    if not value:
        return value
    result = _match(value, _OCCASION_RULES)
    if result:
        return result
    v = value.lower().strip()
    if re.search(r"\s+(?:and|or|/|&)\s+", v):
        v = _take_first(v)
    return v


# ── Consumer profile ──────────────────────────────────────────────────────────

_CONSUMER_RULES: list[tuple[str, str]] = [
    (r"fashion[\s-]forward\s+youth|trend[\s-]conscious|gen[\s-]?z|teenager|"
     r"teen\s+fashion|youth\s+market", "teen trendsetter"),
    (r"working\s+professional|career[\s-]oriented|office\s+worker|"
     r"corporate\s+professional", "young professional"),
    (r"classic\s+dresser|traditional\s+(?:dresser|taste)|mature\s+(?:shopper|buyer|woman|man)|"
     r"conservative\s+dresser", "mature classic"),
    (r"outdoor\s+enthusiast|adventure\s+seeker|active\s+lifestyle", "outdoor enthusiast"),
]


def normalize_consumer_profile(value: str) -> str:
    if not value:
        return value
    result = _match(value, _CONSUMER_RULES)
    if result:
        return result
    v = value.lower().strip()
    if re.search(r"\s+(?:and|or|/|&)\s+", v):
        v = _take_first(v)
    return v


# ── Garment type ─────────────────────────────────────────────────────────────

# Canonical plural → singular mapping (words where the plural is non-canonical)
_GARMENT_PLURALS: dict[str, str] = {
    "sweaters": "sweater",
    "dresses": "dress",
    "jackets": "jacket",
    "coats": "coat",
    "shirts": "shirt",
    "blouses": "blouse",
    "skirts": "skirt",
    "suits": "suit",
    "blazers": "blazer",
    "scarves": "scarf",
    "boots": "boot",
    "tops": "top",
    "hoodies": "hoodie",
    "cardigans": "cardigan",
    "vests": "vest",
    "jumpsuits": "jumpsuit",
}

_GARMENT_TYPE_RULES: list[tuple[str, str]] = [
    # Multi-item descriptions → primary item
    (r"blazer\s+(?:and|&|,)\s+\w+", "blazer"),
    (r"\w+\s+(?:and|&|,)\s+blazer", "blazer"),
    (r"trench\s+coat", "coat"),
    (r"overcoat|peacoat|pea\s+coat|topcoat|trenchcoat", "coat"),
    (r"mixed\s+(?:wardrobe|collection|styles?|pieces?)", "mixed"),
    (r"full\s+(?:outfit|look|ensemble|wardrobe)|mixed\s+outfit", "mixed"),
]


def normalize_garment_type(value: str) -> str:
    if not value:
        return value
    v = value.lower().strip()
    if v in _GARMENT_PLURALS:
        return _GARMENT_PLURALS[v]
    result = _match(v, _GARMENT_TYPE_RULES)
    if result:
        return result
    if re.search(r"\s+(?:and|or|/|&)\s+", v):
        return _take_first(v)
    return v


# ── Entry point ───────────────────────────────────────────────────────────────

def normalize_attributes(attrs: dict) -> dict:
    """Return a copy of attrs with key attributes normalized to reduce filter clutter."""
    result = dict(attrs)
    normalizers = {
        "garment_type": normalize_garment_type,
        "material": normalize_material,
        "style": normalize_style,
        "occasion": normalize_occasion,
        "consumer_profile": normalize_consumer_profile,
    }
    for field, fn in normalizers.items():
        if result.get(field):
            result[field] = fn(result[field])
    return result
