"""Utility helpers for text normalization and CSV field handling."""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Dict, Iterable, List, Optional, Sequence

STOPWORDS_FR_EN = {
    "a",
    "an",
    "and",
    "au",
    "aux",
    "avec",
    "ce",
    "ces",
    "dans",
    "de",
    "des",
    "du",
    "elle",
    "en",
    "et",
    "for",
    "il",
    "ils",
    "in",
    "is",
    "la",
    "le",
    "les",
    "mais",
    "of",
    "on",
    "or",
    "ou",
    "par",
    "pas",
    "pour",
    "que",
    "qui",
    "sur",
    "the",
    "to",
    "un",
    "une",
    "with",
}

SYNONYMS = {
    "basket": "chaussure",
    "baskets": "chaussure",
    "sneaker": "chaussure",
    "sneakers": "chaussure",
    "tel": "telephone",
    "mobile": "telephone",
    "smartphone": "telephone",
    "ordi": "ordinateur",
    "laptop": "ordinateur",
    "notebook": "ordinateur",
    "cadeaux": "cadeau",
    "anniv": "anniversaire",
    "runing": "running",
    "chaussur": "chaussure",
}

COLUMN_CANDIDATES: Dict[str, Sequence[str]] = {
    "title": ("title", "name", "product_name", "nom", "titre", "product"),
    "description": ("description", "desc", "details", "content"),
    "price": ("price", "selling_price", "prix", "amount", "cost"),
    "rating": ("rating", "average_rating", "note", "stars"),
    "image_url": ("image_url", "image", "images", "thumbnail", "photo"),
    "category": ("category", "categorie", "sub_category", "type", "department"),
    "brand": ("brand", "marque", "maker"),
    "url": ("url", "product_url", "link", "href"),
}


def strip_accents(text: str) -> str:
    """Remove accents for robust lexical matching."""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def normalize_text(text: Optional[str], *, keep_spaces: bool = True) -> str:
    """Lowercase, deaccent and remove punctuation/noise."""
    if not text:
        return ""
    cleaned = strip_accents(text.lower())
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if keep_spaces:
        return cleaned
    return cleaned.replace(" ", "")


def tokenize(text: Optional[str]) -> List[str]:
    """Tokenize and remove basic FR/EN stopwords while applying synonym normalization."""
    normalized = normalize_text(text)
    if not normalized:
        return []
    tokens = []
    for token in normalized.split():
        mapped = SYNONYMS.get(token, token)
        if mapped not in STOPWORDS_FR_EN and len(mapped) > 1:
            tokens.append(mapped)
    return tokens


def parse_numeric(value: Optional[str]) -> Optional[float]:
    """Parse numbers safely from messy CSV values (e.g. '2,309', '30%')."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    cleaned = raw.replace(" ", "")
    cleaned = cleaned.replace("%", "")
    if "," in cleaned and "." not in cleaned:
        if cleaned.count(",") == 1 and len(cleaned.split(",")[1]) <= 2:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
    if not cleaned or cleaned in {"-", "."}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_column_map(raw_value: Optional[str]) -> Dict[str, str]:
    """Load optional user column mapping from JSON string."""
    if not raw_value:
        return {}
    try:
        payload = json.loads(raw_value)
        if isinstance(payload, dict):
            return {str(k): str(v) for k, v in payload.items()}
    except json.JSONDecodeError:
        return {}
    return {}


def detect_columns(headers: Iterable[str], override: Optional[Dict[str, str]] = None) -> Dict[str, Optional[str]]:
    """Heuristic column detection with optional explicit overrides."""
    available = [h.strip() for h in headers if h]
    normalized_to_original = {normalize_text(h, keep_spaces=False): h for h in available}
    mapping: Dict[str, Optional[str]] = {key: None for key in COLUMN_CANDIDATES}

    if override:
        for canonical, chosen in override.items():
            if chosen in available:
                mapping[canonical] = chosen

    for canonical, candidates in COLUMN_CANDIDATES.items():
        if mapping.get(canonical):
            continue
        for candidate in candidates:
            key = normalize_text(candidate, keep_spaces=False)
            if key in normalized_to_original:
                mapping[canonical] = normalized_to_original[key]
                break
    return mapping
