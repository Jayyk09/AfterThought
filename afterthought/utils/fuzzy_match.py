"""Fuzzy string matching utilities."""

from typing import List, Tuple

from thefuzz import fuzz, process


def fuzzy_match(
    query: str,
    choices: List[str],
    threshold: int = 60,
    limit: int = 5,
) -> List[Tuple[str, int]]:
    """
    Fuzzy match a query against a list of choices.

    Args:
        query: String to search for
        choices: List of strings to search in
        threshold: Minimum match score (0-100), default 60
        limit: Maximum number of results to return

    Returns:
        List of (match, score) tuples, sorted by score descending
    """
    if not query or not choices:
        return []

    # Use token_sort_ratio for better matching (handles word order)
    matches = process.extract(
        query,
        choices,
        scorer=fuzz.token_sort_ratio,
        limit=limit
    )

    # Filter by threshold
    return [(match, score) for match, score, _ in matches if score >= threshold]


def best_match(
    query: str,
    choices: List[str],
    threshold: int = 60,
) -> Tuple[str, int]:
    """
    Get the best fuzzy match for a query.

    Args:
        query: String to search for
        choices: List of strings to search in
        threshold: Minimum match score (0-100)

    Returns:
        Tuple of (best_match, score), or (None, 0) if no match above threshold

    Raises:
        ValueError: If no matches found above threshold
    """
    matches = fuzzy_match(query, choices, threshold=threshold, limit=1)

    if not matches:
        raise ValueError(f"No matches found for '{query}' (threshold: {threshold})")

    return matches[0]


def match_score(str1: str, str2: str) -> int:
    """
    Calculate fuzzy match score between two strings.

    Args:
        str1: First string
        str2: Second string

    Returns:
        Match score (0-100)
    """
    return fuzz.token_sort_ratio(str1, str2)
