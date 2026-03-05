"""
Boundary Detection Utilities

Provides utilities for detecting text boundaries at various levels:
- Sentence boundaries
- Paragraph boundaries
- Word boundaries

Used by the structure-aware chunker for finding optimal split points.
"""

import re
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class BoundaryInfo:
    """Information about a detected boundary."""

    position: int  # Character position in text
    boundary_type: str  # "sentence", "paragraph", "word"
    confidence: float = 1.0  # Confidence score (0-1)


class BoundaryDetector:
    """
    Detects text boundaries for chunking purposes.

    Supports multiple languages with customizable patterns.
    """

    # Sentence-ending punctuation patterns by language
    SENTENCE_PATTERNS = {
        "en": [
            # Standard sentence endings followed by space and capital
            (r"(?<=[.!?])\s+(?=[A-Z])", 0.95),
            # Sentence end at newline
            (r"(?<=[.!?])\s*\n", 0.9),
            # Sentence end at end of text
            (r"(?<=[.!?])\s*$", 0.85),
            # Abbreviation-aware (avoid Mr., Dr., etc.)
            (r"(?<![A-Z][a-z])\.\s+(?=[A-Z])", 0.8),
        ],
    }

    # Paragraph patterns
    PARAGRAPH_PATTERNS = [
        (r"\n\s*\n", 0.95),  # Double newline
        (r"\n(?=\s{4,})", 0.7),  # Newline followed by indent
    ]

    def __init__(self, language: str = "en"):
        """
        Initialize boundary detector.

        Args:
            language: Language code for pattern selection
        """
        self.language = language
        self._sentence_patterns = self._compile_patterns(
            self.SENTENCE_PATTERNS.get(language, self.SENTENCE_PATTERNS["en"])
        )
        self._paragraph_patterns = self._compile_patterns(self.PARAGRAPH_PATTERNS)

    def _compile_patterns(
        self, patterns: List[Tuple[str, float]]
    ) -> List[Tuple[re.Pattern, float]]:
        """Compile regex patterns."""
        return [(re.compile(p), conf) for p, conf in patterns]

    def split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        if not text or not text.strip():
            return []

        # Find all sentence boundaries
        boundaries = self.find_sentence_boundaries(text)

        if not boundaries:
            return [text.strip()]

        # Split at boundaries
        sentences = []
        start = 0
        for boundary in boundaries:
            sentence = text[start : boundary.position].strip()
            if sentence:
                sentences.append(sentence)
            start = boundary.position

        # Add final segment
        final = text[start:].strip()
        if final:
            sentences.append(final)

        return sentences

    def find_sentence_boundaries(self, text: str) -> List[BoundaryInfo]:
        """
        Find all sentence boundaries in text.

        Args:
            text: Text to analyze

        Returns:
            List of BoundaryInfo objects sorted by position
        """
        boundaries = []

        for pattern, confidence in self._sentence_patterns:
            for match in pattern.finditer(text):
                boundaries.append(
                    BoundaryInfo(
                        position=match.end(),
                        boundary_type="sentence",
                        confidence=confidence,
                    )
                )

        # Sort by position and deduplicate
        boundaries.sort(key=lambda b: b.position)
        return self._deduplicate_boundaries(boundaries)

    def find_paragraph_boundaries(self, text: str) -> List[BoundaryInfo]:
        """
        Find all paragraph boundaries in text.

        Args:
            text: Text to analyze

        Returns:
            List of BoundaryInfo objects sorted by position
        """
        boundaries = []

        for pattern, confidence in self._paragraph_patterns:
            for match in pattern.finditer(text):
                boundaries.append(
                    BoundaryInfo(
                        position=match.end(),
                        boundary_type="paragraph",
                        confidence=confidence,
                    )
                )

        boundaries.sort(key=lambda b: b.position)
        return self._deduplicate_boundaries(boundaries)

    def find_word_boundaries(self, text: str) -> List[BoundaryInfo]:
        """
        Find all word boundaries in text.

        Args:
            text: Text to analyze

        Returns:
            List of BoundaryInfo objects sorted by position
        """
        boundaries = []
        word_pattern = re.compile(r"\s+")

        for match in word_pattern.finditer(text):
            boundaries.append(
                BoundaryInfo(
                    position=match.end(),
                    boundary_type="word",
                    confidence=1.0,
                )
            )

        return boundaries

    def find_best_boundary_near(
        self,
        text: str,
        target_position: int,
        search_range: int = 50,
        prefer_types: List[str] = None,
    ) -> BoundaryInfo:
        """
        Find the best boundary near a target position.

        Prefers sentence > paragraph > word boundaries.

        Args:
            text: Text to search
            target_position: Target character position
            search_range: Number of characters to search before/after target
            prefer_types: Preferred boundary types in order

        Returns:
            BoundaryInfo for best boundary found
        """
        prefer_types = prefer_types or ["sentence", "paragraph", "word"]

        # Define search window
        start = max(0, target_position - search_range)
        end = min(len(text), target_position + search_range)

        # Find all boundaries in window
        candidates = []

        sentence_bounds = self.find_sentence_boundaries(text)
        for b in sentence_bounds:
            if start <= b.position <= end:
                candidates.append(b)

        para_bounds = self.find_paragraph_boundaries(text)
        for b in para_bounds:
            if start <= b.position <= end:
                candidates.append(b)

        word_bounds = self.find_word_boundaries(text)
        for b in word_bounds:
            if start <= b.position <= end:
                candidates.append(b)

        if not candidates:
            # No boundary found, return target position as word boundary
            return BoundaryInfo(
                position=target_position,
                boundary_type="character",
                confidence=0.5,
            )

        # Score candidates by type preference and distance
        def score(boundary: BoundaryInfo) -> float:
            type_score = (
                len(prefer_types) - prefer_types.index(boundary.boundary_type)
                if boundary.boundary_type in prefer_types
                else 0
            )
            distance_score = 1.0 - (
                abs(boundary.position - target_position) / search_range
            )
            return type_score * 10 + distance_score + boundary.confidence

        candidates.sort(key=score, reverse=True)
        return candidates[0]

    def _deduplicate_boundaries(
        self, boundaries: List[BoundaryInfo], threshold: int = 3
    ) -> List[BoundaryInfo]:
        """Remove duplicate boundaries that are too close together."""
        if not boundaries:
            return []

        result = [boundaries[0]]
        for b in boundaries[1:]:
            if b.position - result[-1].position > threshold:
                result.append(b)
            elif b.confidence > result[-1].confidence:
                result[-1] = b

        return result


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def estimate_position_for_word_count(text: str, target_words: int) -> int:
    """
    Estimate character position for a target word count.

    Args:
        text: Text to analyze
        target_words: Target number of words

    Returns:
        Estimated character position
    """
    words = text.split()
    if target_words >= len(words):
        return len(text)

    # Count characters up to target word
    position = 0
    for i, word in enumerate(words[:target_words]):
        position = text.find(word, position) + len(word)

    return position
