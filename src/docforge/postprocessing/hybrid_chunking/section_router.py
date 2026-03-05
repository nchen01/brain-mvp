"""
Section Router

Length-based routing for sections to determine chunking strategy.

Routes sections to one of three categories:
- SHORT: Keep as single chunk or merge with adjacent short sections
- MEDIUM: Recursive split at paragraph/sentence boundaries
- LONG: Recursive split + flag for semantic refinement
"""

import logging
from typing import List

from .interfaces import ISectionRouter
from .normalized_document import NormalizedSection
from .config import HybridChunkingConfig, SectionSizeCategory

logger = logging.getLogger(__name__)


class SectionRouter(ISectionRouter):
    """
    Routes sections to appropriate chunking strategies based on length.

    The router classifies sections by word count and determines:
    1. Which chunking strategy to apply
    2. Whether adjacent short sections should be merged
    3. Whether chunks should be flagged for semantic refinement
    """

    def __init__(self, config: HybridChunkingConfig = None):
        """
        Initialize section router.

        Args:
            config: Chunking configuration with thresholds
        """
        self.config = config or HybridChunkingConfig()

    def classify_section(self, section: NormalizedSection) -> SectionSizeCategory:
        """
        Classify section as SHORT, MEDIUM, or LONG based on word count.

        Args:
            section: NormalizedSection to classify

        Returns:
            SectionSizeCategory enum value
        """
        word_count = section.word_count

        if word_count < self.config.short_section_threshold:
            return SectionSizeCategory.SHORT
        elif word_count > self.config.long_section_threshold:
            return SectionSizeCategory.LONG
        else:
            return SectionSizeCategory.MEDIUM

    def route_section(self, section: NormalizedSection) -> str:
        """
        Determine chunking strategy for a section.

        Args:
            section: NormalizedSection to route

        Returns:
            Strategy name:
            - "keep_or_merge": Keep as single chunk or merge with adjacent
            - "recursive_paragraph_sentence": Split at paragraph/sentence boundaries
            - "recursive_with_semantic_flag": Same as above but flag for refinement
        """
        category = self.classify_section(section)

        if category == SectionSizeCategory.SHORT:
            return "keep_or_merge"
        elif category == SectionSizeCategory.MEDIUM:
            return "recursive_paragraph_sentence"
        else:  # LONG
            return "recursive_with_semantic_flag"

    def group_mergeable_sections(
        self, sections: List[NormalizedSection]
    ) -> List[List[NormalizedSection]]:
        """
        Group adjacent short sections that can be merged.

        This method groups sections for processing:
        - SHORT sections may be grouped together if their combined word count
          is within the merge threshold
        - MEDIUM and LONG sections are always in their own group

        Args:
            sections: List of sections to analyze (should be in document order)

        Returns:
            List of section groups. Each group is either:
            - A single MEDIUM/LONG section
            - One or more SHORT sections to be merged
        """
        if not sections:
            return []

        groups: List[List[NormalizedSection]] = []
        current_group: List[NormalizedSection] = []
        current_word_count = 0

        for section in sections:
            category = self.classify_section(section)

            if category != SectionSizeCategory.SHORT:
                # Non-short section: finalize current group, add as single
                if current_group:
                    groups.append(current_group)
                    current_group = []
                    current_word_count = 0
                groups.append([section])
            else:
                # Short section: try to add to current group
                if self._can_merge(current_word_count, section.word_count):
                    current_group.append(section)
                    current_word_count += section.word_count
                else:
                    # Group is full, start new one
                    if current_group:
                        groups.append(current_group)
                    current_group = [section]
                    current_word_count = section.word_count

        # Don't forget the last group
        if current_group:
            groups.append(current_group)

        return groups

    def _can_merge(self, current_count: int, additional_count: int) -> bool:
        """
        Check if additional content can be merged with current group.

        Args:
            current_count: Current word count in group
            additional_count: Word count to add

        Returns:
            True if merge is allowed
        """
        if not self.config.merge_adjacent_short_sections:
            return current_count == 0  # Only allow first item

        combined = current_count + additional_count
        return combined <= self.config.short_section_merge_threshold

    def should_flag_for_semantic(self, section: NormalizedSection) -> bool:
        """
        Determine if section's chunks should be flagged for semantic refinement.

        Args:
            section: Section to check

        Returns:
            True if chunks should be flagged
        """
        if not self.config.flag_long_sections_for_semantic:
            return False

        return self.classify_section(section) == SectionSizeCategory.LONG

    def get_routing_info(self, section: NormalizedSection) -> dict:
        """
        Get detailed routing information for a section.

        Args:
            section: Section to analyze

        Returns:
            Dictionary with routing details
        """
        category = self.classify_section(section)
        strategy = self.route_section(section)

        return {
            "section_id": section.id,
            "word_count": section.word_count,
            "category": category.value,
            "strategy": strategy,
            "flag_for_semantic": self.should_flag_for_semantic(section),
            "heading": section.heading_text,
            "heading_level": section.heading_level,
            "paragraph_count": len(section.paragraphs),
        }

    def analyze_document_sections(
        self, sections: List[NormalizedSection]
    ) -> dict:
        """
        Analyze all sections in a document for routing statistics.

        Args:
            sections: List of all sections (can be nested)

        Returns:
            Dictionary with routing statistics
        """
        stats = {
            "total_sections": 0,
            "short_count": 0,
            "medium_count": 0,
            "long_count": 0,
            "mergeable_groups": 0,
            "total_word_count": 0,
        }

        # Flatten nested sections
        all_sections = self._flatten_sections(sections)
        stats["total_sections"] = len(all_sections)

        for section in all_sections:
            category = self.classify_section(section)
            stats["total_word_count"] += section.word_count

            if category == SectionSizeCategory.SHORT:
                stats["short_count"] += 1
            elif category == SectionSizeCategory.MEDIUM:
                stats["medium_count"] += 1
            else:
                stats["long_count"] += 1

        # Count mergeable groups
        groups = self.group_mergeable_sections(all_sections)
        stats["mergeable_groups"] = sum(1 for g in groups if len(g) > 1)

        return stats

    def _flatten_sections(
        self, sections: List[NormalizedSection]
    ) -> List[NormalizedSection]:
        """Flatten nested sections into a single list."""
        result = []
        for section in sections:
            result.append(section)
            if section.children:
                result.extend(self._flatten_sections(section.children))
        return result
