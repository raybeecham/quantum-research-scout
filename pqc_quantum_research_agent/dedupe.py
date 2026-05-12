from __future__ import annotations

from difflib import SequenceMatcher

from .models import ExistingItem, ResearchItem
from .text import canonicalize_url, normalize_title, title_hash


def prepare_identity(item: ResearchItem) -> ResearchItem:
    item.canonical_url = canonicalize_url(item.url)
    item.title_normalized = normalize_title(item.title)
    item.title_hash = title_hash(item.title)
    return item


def dedupe_items(
    items: list[ResearchItem],
    existing_items: list[ExistingItem],
    fuzzy_threshold: float = 0.92,
) -> list[ResearchItem]:
    seen_urls = {item.canonical_url for item in existing_items if item.canonical_url}
    seen_hashes = {item.title_hash for item in existing_items if item.title_hash}
    seen_titles = [item.title_normalized for item in existing_items if item.title_normalized]
    unique_items: list[ResearchItem] = []

    for item in items:
        prepare_identity(item)
        if not item.canonical_url or not item.title_normalized:
            continue
        if item.canonical_url in seen_urls:
            continue
        if item.title_hash in seen_hashes:
            continue
        if _has_fuzzy_match(item.title_normalized, seen_titles, fuzzy_threshold):
            continue

        unique_items.append(item)
        seen_urls.add(item.canonical_url)
        seen_hashes.add(item.title_hash)
        seen_titles.append(item.title_normalized)

    return unique_items


def _has_fuzzy_match(title: str, candidates: list[str], threshold: float) -> bool:
    if len(title) < 12:
        return False
    for candidate in candidates:
        if abs(len(title) - len(candidate)) > max(20, len(title) * 0.35):
            continue
        if SequenceMatcher(None, title, candidate).ratio() >= threshold:
            return True
    return False
