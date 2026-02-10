"""Abbreviation expansion system for post-processing."""

import logging
import re
import json
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
from dataclasses import dataclass

from docforge.preprocessing.schemas import StandardizedDocumentOutput
from .schemas import AbbreviationMapping

logger = logging.getLogger(__name__)


@dataclass
class AbbreviationContext:
    """Context information for abbreviation detection."""
    sentence: str
    paragraph: str
    document_type: str
    domain: str
    surrounding_words: List[str]


class AbbreviationDatabase:
    """Database of abbreviations and their expansions."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the abbreviation database."""
        self.db_path = db_path or "data/abbreviations.json"
        self.abbreviations: Dict[str, List[AbbreviationMapping]] = {}
        self.domain_patterns: Dict[str, List[re.Pattern]] = {}
        self._load_database()
    
    def _load_database(self):
        """Load abbreviations from database file."""
        try:
            db_file = Path(self.db_path)
            if db_file.exists():
                with open(db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Load abbreviations
                for abbrev, mappings in data.get('abbreviations', {}).items():
                    self.abbreviations[abbrev.upper()] = [
                        AbbreviationMapping(**mapping) for mapping in mappings
                    ]
                
                logger.info(f"Loaded {len(self.abbreviations)} abbreviations from database")
            else:
                # Initialize with default abbreviations
                self._create_default_database()
                self._save_database()
                
        except Exception as e:
            logger.error(f"Error loading abbreviation database: {e}")
            self._create_default_database()
    
    def _create_default_database(self):
        """Create default abbreviation database."""
        default_abbreviations = {
            # Technical abbreviations
            'API': [
                AbbreviationMapping(
                    abbreviation='API',
                    expansion='Application Programming Interface',
                    domain='technical',
                    confidence=0.95
                )
            ],
            'HTTP': [
                AbbreviationMapping(
                    abbreviation='HTTP',
                    expansion='HyperText Transfer Protocol',
                    domain='technical',
                    confidence=0.98
                )
            ],
            'JSON': [
                AbbreviationMapping(
                    abbreviation='JSON',
                    expansion='JavaScript Object Notation',
                    domain='technical',
                    confidence=0.95
                )
            ],
            'REST': [
                AbbreviationMapping(
                    abbreviation='REST',
                    expansion='Representational State Transfer',
                    domain='technical',
                    confidence=0.90
                )
            ],
            'SQL': [
                AbbreviationMapping(
                    abbreviation='SQL',
                    expansion='Structured Query Language',
                    domain='technical',
                    confidence=0.98
                )
            ],
            'URL': [
                AbbreviationMapping(
                    abbreviation='URL',
                    expansion='Uniform Resource Locator',
                    domain='technical',
                    confidence=0.95
                )
            ],
            'XML': [
                AbbreviationMapping(
                    abbreviation='XML',
                    expansion='eXtensible Markup Language',
                    domain='technical',
                    confidence=0.95
                )
            ],
            
            # Academic abbreviations
            'AI': [
                AbbreviationMapping(
                    abbreviation='AI',
                    expansion='Artificial Intelligence',
                    domain='academic',
                    confidence=0.90
                )
            ],
            'ML': [
                AbbreviationMapping(
                    abbreviation='ML',
                    expansion='Machine Learning',
                    domain='academic',
                    confidence=0.85
                )
            ],
            'NLP': [
                AbbreviationMapping(
                    abbreviation='NLP',
                    expansion='Natural Language Processing',
                    domain='academic',
                    confidence=0.90
                )
            ],
            'CV': [
                AbbreviationMapping(
                    abbreviation='CV',
                    expansion='Computer Vision',
                    domain='academic',
                    confidence=0.70,
                    context='computer science'
                ),
                AbbreviationMapping(
                    abbreviation='CV',
                    expansion='Curriculum Vitae',
                    domain='general',
                    confidence=0.80,
                    context='resume'
                )
            ],
            
            # Business abbreviations
            'CEO': [
                AbbreviationMapping(
                    abbreviation='CEO',
                    expansion='Chief Executive Officer',
                    domain='business',
                    confidence=0.98
                )
            ],
            'CTO': [
                AbbreviationMapping(
                    abbreviation='CTO',
                    expansion='Chief Technology Officer',
                    domain='business',
                    confidence=0.95
                )
            ],
            'ROI': [
                AbbreviationMapping(
                    abbreviation='ROI',
                    expansion='Return on Investment',
                    domain='business',
                    confidence=0.90
                )
            ],
            
            # General abbreviations
            'USA': [
                AbbreviationMapping(
                    abbreviation='USA',
                    expansion='United States of America',
                    domain='general',
                    confidence=0.98
                )
            ],
            'UK': [
                AbbreviationMapping(
                    abbreviation='UK',
                    expansion='United Kingdom',
                    domain='general',
                    confidence=0.95
                )
            ],
            'EU': [
                AbbreviationMapping(
                    abbreviation='EU',
                    expansion='European Union',
                    domain='general',
                    confidence=0.90
                )
            ]
        }
        
        self.abbreviations = default_abbreviations
    
    def _save_database(self):
        """Save abbreviations to database file."""
        try:
            db_file = Path(self.db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to serializable format
            data = {
                'abbreviations': {
                    abbrev: [mapping.model_dump() for mapping in mappings]
                    for abbrev, mappings in self.abbreviations.items()
                }
            }
            
            with open(db_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Error saving abbreviation database: {e}")
    
    def get_expansions(self, abbreviation: str, domain: Optional[str] = None) -> List[AbbreviationMapping]:
        """Get possible expansions for an abbreviation."""
        abbrev_upper = abbreviation.upper()
        mappings = self.abbreviations.get(abbrev_upper, [])
        
        if domain:
            # Filter by domain
            domain_mappings = [m for m in mappings if m.domain == domain]
            if domain_mappings:
                return domain_mappings
        
        return mappings
    
    def add_abbreviation(self, mapping: AbbreviationMapping):
        """Add a new abbreviation mapping."""
        abbrev_upper = mapping.abbreviation.upper()
        
        if abbrev_upper not in self.abbreviations:
            self.abbreviations[abbrev_upper] = []
        
        # Check if mapping already exists
        existing = self.abbreviations[abbrev_upper]
        for existing_mapping in existing:
            if (existing_mapping.expansion == mapping.expansion and 
                existing_mapping.domain == mapping.domain):
                # Update confidence if higher
                if mapping.confidence > existing_mapping.confidence:
                    existing_mapping.confidence = mapping.confidence
                return
        
        # Add new mapping
        self.abbreviations[abbrev_upper].append(mapping)
        self._save_database()
    
    def get_all_abbreviations(self) -> Set[str]:
        """Get all known abbreviations."""
        return set(self.abbreviations.keys())


class AbbreviationDetector:
    """Detects abbreviations in text."""
    
    def __init__(self):
        """Initialize the abbreviation detector."""
        self.abbreviation_patterns = [
            # Standard abbreviation pattern (2-5 uppercase letters)
            re.compile(r'\b[A-Z]{2,5}\b'),

            # Abbreviation with periods (e.g., U.S.A.)
            re.compile(r'\b[A-Z](?:\.[A-Z])+\.?\b'),

            # Mixed case abbreviations (e.g., PhD, MSc, BSc, IoT)
            re.compile(r'\b[A-Z][a-z]*[A-Z][a-z]*\b'),

            # Academic degrees (e.g., PhD, MSc, BSc)
            re.compile(r'\b[A-Z][a-z]?[A-Z]\b'),

            # Abbreviations with ampersand (e.g., O&M, R&D, M&A)
            re.compile(r'\b[A-Z]&[A-Z]\b'),
        ]
        
        # Common words that look like abbreviations but aren't
        self.false_positives = {
            'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE',
            'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HIS', 'HOW', 'ITS', 'MAY', 'NEW', 'NOW',
            'OLD', 'SEE', 'TWO', 'WHO', 'BOY', 'DID', 'ITS', 'LET', 'PUT', 'SAY', 'SHE', 'TOO',
            'USE', 'WAY', 'WHY', 'YOU', 'ANY', 'ASK', 'BAD', 'BAG', 'BED', 'BIG', 'BOX', 'BUS',
            'CAR', 'CAT', 'CUP', 'CUT', 'DOG', 'EAR', 'EAT', 'EGG', 'END', 'EYE', 'FAR', 'FUN',
            'GOT', 'GUN', 'HAD', 'HAT', 'HIT', 'HOT', 'JOB', 'LAW', 'LEG', 'LET', 'LOT', 'LOW',
            'MAN', 'MAP', 'MOM', 'PEN', 'PET', 'PIG', 'RAN', 'RED', 'RUN', 'SAD', 'SAT', 'SUN',
            'TEN', 'TOP', 'VAN', 'WAR', 'WIN', 'YES', 'YET', 'ZOO'
        }
    
    def detect_abbreviations(self, text: str, context: Optional[AbbreviationContext] = None) -> List[Tuple[str, int, int]]:
        """Detect abbreviations in text.
        
        Returns:
            List of tuples (abbreviation, start_pos, end_pos)
        """
        abbreviations = []
        
        for pattern in self.abbreviation_patterns:
            for match in pattern.finditer(text):
                abbrev = match.group()
                
                # Skip false positives
                if abbrev.upper() in self.false_positives:
                    continue
                
                # Skip single letters unless they're common abbreviations
                if len(abbrev) == 1 and abbrev.upper() not in {'I', 'A'}:
                    continue
                
                # Additional context-based filtering
                if self._is_likely_abbreviation(abbrev, text, match.start(), context):
                    abbreviations.append((abbrev, match.start(), match.end()))
        
        return abbreviations
    
    def _is_likely_abbreviation(self, abbrev: str, text: str, position: int, context: Optional[AbbreviationContext]) -> bool:
        """Determine if a detected pattern is likely an abbreviation."""
        # Check if it's at the beginning of a sentence (more likely to be abbreviation)
        sentence_start = text.rfind('.', 0, position)
        if sentence_start != -1:
            between_text = text[sentence_start + 1:position].strip()
            if not between_text:  # At sentence start
                return True
        
        # Check surrounding context
        start = max(0, position - 50)
        end = min(len(text), position + len(abbrev) + 50)
        surrounding = text[start:end].lower()
        
        # Look for expansion patterns nearby
        expansion_indicators = [
            f'{abbrev.lower()} (',  # "API (Application Programming Interface)"
            f'({abbrev.lower()})',  # "Application Programming Interface (API)"
            f'{abbrev.lower()} stands for',
            f'{abbrev.lower()} is short for',
        ]
        
        for indicator in expansion_indicators:
            if indicator in surrounding:
                return True
        
        # If we have context, use domain-specific rules
        if context:
            if context.domain == 'technical' and len(abbrev) >= 2:
                return True
            elif context.domain == 'academic' and len(abbrev) >= 2:
                return True
        
        # Default: likely if 2+ characters and (all uppercase OR mixed case academic degrees)
        if len(abbrev) >= 2:
            if abbrev.isupper():
                return True
            # Check for common academic degree patterns
            academic_patterns = ['PhD', 'MSc', 'BSc', 'MBA', 'MD', 'JD', 'LLB', 'LLM']
            if abbrev in academic_patterns:
                return True
        
        return False


class AbbreviationExpander:
    """Main abbreviation expansion system."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the abbreviation expander."""
        self.database = AbbreviationDatabase(db_path)
        self.detector = AbbreviationDetector()
        self.expansion_cache: Dict[str, str] = {}
        # Track abbreviation definitions found in the current document
        self._document_definitions: Dict[str, str] = {}

    def _pre_scan_document(self, document: StandardizedDocumentOutput) -> List[AbbreviationMapping]:
        """
        Pre-scan the document for inline abbreviation definitions.

        Detects both common academic patterns:
          - "ABBREV (Full Form)" - e.g., "PSC (perovskite solar cells)" [Primary]
          - "Full Form (ABBREV)" - e.g., "perovskite solar cells (PSC)" [Secondary]

        Pattern 1 (ABBREV followed by parenthesized expansion) is run first because
        it is more reliable - the expansion text is explicitly in the parentheses.
        Pattern 2 (backwards matching) is only used for abbreviations not found by Pattern 1.

        First occurrence wins: once a definition is found for an abbreviation, later
        occurrences are ignored to prefer the original definition site.

        Returns:
            List of discovered AbbreviationMapping objects
        """
        self._document_definitions = {}
        discovered = []
        text = document.plain_text or ""

        if not text:
            return discovered

        # === Pattern 1 (Primary): ABBREV (full form) ===
        # Most reliable: expansion is explicitly in parentheses after the abbreviation.
        # Examples: "PSC (perovskite solar cells)", "PL (photoluminescence)"
        # We accept expansions based on positional evidence without requiring strict
        # initials matching, since many scientific abbreviations (VOC, JSC) don't
        # follow standard initial-letter conventions.
        patterns_abbrev_then_full = [
            # Standard: all uppercase (e.g., PSC, API, FAIR)
            re.compile(r'\b([A-Z][A-Z0-9]{1,9})\s*\(([^)]{3,80})\)'),
            # Mixed case: e.g., IoT, PhD, eBay
            re.compile(r'\b([A-Z][a-z]*[A-Z][a-z]*)\s*\(([^)]{3,80})\)'),
            # With ampersand: e.g., O&M, R&D, M&A
            re.compile(r'\b([A-Z]&[A-Z])\s*;?\s*\(([^)]{3,80})\)'),
        ]

        for pattern in patterns_abbrev_then_full:
            for match in pattern.finditer(text):
                abbrev = match.group(1)
                paren_content = match.group(2).strip()

                if abbrev.upper() in self._document_definitions:
                    continue  # First occurrence wins

                # Skip if the parenthesized content is all uppercase (likely another abbreviation)
                if paren_content.isupper():
                    continue

                # Skip if parenthesized content looks like a citation, reference, or number
                if re.match(r'^[\d]', paren_content):
                    continue
                if paren_content.lower().startswith(('see ', 'cf.', 'fig.', 'eq.', 'ref.')):
                    continue

                # Accept the expansion if the content looks like a definition:
                words = paren_content.split()
                is_likely_expansion = False
                confidence = 0.85

                if len(words) >= 2 and not paren_content.isupper():
                    # Multi-word expansion (most common case)
                    is_likely_expansion = True
                    # Boost confidence if initials match strictly
                    if self._initials_match(abbrev, paren_content):
                        confidence = 0.95
                    else:
                        confidence = 0.88
                elif len(words) == 1 and len(paren_content) > len(abbrev) and not paren_content.isupper():
                    # Single-word expansion like "photoluminescence" for PL
                    # Must be longer than the abbreviation and not all caps
                    is_likely_expansion = True
                    confidence = 0.85

                if is_likely_expansion:
                    mapping = AbbreviationMapping(
                        abbreviation=abbrev,
                        expansion=paren_content,
                        domain='document',
                        confidence=confidence,
                        source='document_pre_scan'
                    )
                    self.database.add_abbreviation(mapping)
                    discovered.append(mapping)
                    self._document_definitions[abbrev.upper()] = paren_content
                    logger.debug(f"Pre-scan discovered (ABBREV->def): {abbrev} -> {paren_content}")

        # === Pattern 2 (Secondary): Full Form (ABBREV) ===
        # Find "(ABBREV)" and look backwards for the full form.
        # Only used for abbreviations NOT already found by Pattern 1.
        paren_abbrev_patterns = [
            # Standard: all uppercase (e.g., PSC, API, FAIR)
            re.compile(r'\(([A-Z][A-Z0-9]{1,9}s?)\)'),
            # Mixed case: e.g., IoT, PhD
            re.compile(r'\(([A-Z][a-z]*[A-Z][a-z]*)\)'),
            # With ampersand: e.g., O&M, R&D
            re.compile(r'\(([A-Z]&[A-Z])\)'),
        ]

        for paren_pattern in paren_abbrev_patterns:
            for match in paren_pattern.finditer(text):
                raw_abbrev = match.group(1)
                abbrev = raw_abbrev.rstrip('s')  # Strip plural 's'
                paren_start = match.start()

                if abbrev.upper() in self._document_definitions:
                    continue

                # Get the text before the parenthesis (up to 200 chars back)
                lookback_start = max(0, paren_start - 200)
                preceding_text = text[lookback_start:paren_start].rstrip()

                # Extract the full form by matching initials backwards
                full_form = self._extract_full_form_backwards(abbrev, preceding_text)

                if full_form:
                    for ab in set([abbrev, raw_abbrev]):
                        if ab.upper() not in self._document_definitions:
                            mapping = AbbreviationMapping(
                                abbreviation=ab,
                                expansion=full_form,
                                domain='document',
                                confidence=0.90,
                                source='document_pre_scan'
                            )
                            self.database.add_abbreviation(mapping)
                            discovered.append(mapping)
                            self._document_definitions[ab.upper()] = full_form
                            logger.debug(f"Pre-scan discovered (def->ABBREV): {ab} -> {full_form}")

        if discovered:
            logger.info(
                f"Pre-scan found {len(discovered)} abbreviation definitions in document: "
                f"{', '.join(d.abbreviation + ' -> ' + d.expansion for d in discovered)}"
            )

        return discovered

    def _extract_full_form_backwards(self, abbrev: str, preceding_text: str) -> Optional[str]:
        """
        Extract the full form of an abbreviation by matching initials backwards.

        Given abbreviation "PCE" and preceding text "...a sharp upswing of power conversion efficiency",
        works backwards:
          - "efficiency" -> 'E' matches PCE[2] ✓
          - "conversion" -> 'C' matches PCE[1] ✓
          - "power" -> 'P' matches PCE[0] ✓
          → returns "power conversion efficiency"

        Handles hyphenated words (e.g., "metal-insulator-semiconductor" contributes M, I, S).
        Skips common prepositions/articles when they don't match.
        """
        if not preceding_text or len(abbrev) < 2:
            return None

        # Split preceding text into words (preserve order)
        words = preceding_text.split()
        if not words:
            return None

        abbrev_upper = abbrev.upper()
        abbrev_len = len(abbrev_upper)

        # Try to match from the end of preceding text backwards
        # Each word (or hyphenated sub-word) should match one letter of the abbreviation
        matched_words = []
        abbrev_idx = abbrev_len - 1  # Start from last letter

        skip_words = {'a', 'an', 'the', 'of', 'in', 'on', 'at', 'to', 'for', 'and', 'or', 'by', 'with', 'is'}

        for word in reversed(words):
            if abbrev_idx < 0:
                break

            # Clean the word (remove punctuation at edges)
            clean_word = re.sub(r'^[^A-Za-z]+|[^A-Za-z]+$', '', word)
            if not clean_word:
                continue

            # Handle hyphenated words: "metal-insulator-semiconductor" → [metal, insulator, semiconductor]
            if '-' in clean_word:
                sub_words = [sw for sw in clean_word.split('-') if sw]
                # Try matching sub-words in reverse
                sub_matched = []
                temp_idx = abbrev_idx
                for sub_word in reversed(sub_words):
                    if temp_idx < 0:
                        break
                    if sub_word[0].upper() == abbrev_upper[temp_idx]:
                        sub_matched.insert(0, sub_word)
                        temp_idx -= 1
                    else:
                        break

                if sub_matched and len(sub_matched) > 0 and temp_idx < abbrev_idx:
                    matched_words.insert(0, clean_word)
                    abbrev_idx = temp_idx
                    continue

            # Single word matching
            first_letter = clean_word[0].upper()
            if first_letter == abbrev_upper[abbrev_idx]:
                matched_words.insert(0, clean_word)
                abbrev_idx -= 1
            elif clean_word.lower() in skip_words:
                # Include skippable words between matched words for readability
                # but only if we've already started matching
                if matched_words:
                    matched_words.insert(0, clean_word)
            else:
                # Non-matching, non-skippable word - stop if we've started matching
                if matched_words:
                    break

        # Check if all abbreviation letters were matched
        if abbrev_idx >= 0:
            return None

        full_form = ' '.join(matched_words)

        # Final sanity checks
        if len(full_form) < 3:
            return None

        return full_form

    def _initials_match(self, abbrev: str, full_form: str) -> bool:
        """Check if initials of full_form match the abbreviation."""
        skip_words = {'a', 'an', 'the', 'of', 'in', 'on', 'at', 'to', 'for', 'and', 'or', 'by', 'with'}
        words = full_form.split()
        initials = []
        for word in words:
            clean = re.sub(r'^[^A-Za-z]+|[^A-Za-z]+$', '', word)
            if not clean:
                continue
            if '-' in clean:
                for sub in clean.split('-'):
                    if sub and sub.lower() not in skip_words:
                        initials.append(sub[0].upper())
            elif clean.lower() not in skip_words:
                initials.append(clean[0].upper())

        return ''.join(initials) == abbrev.upper()

    def expand_abbreviations(
        self,
        document: StandardizedDocumentOutput,
        domains: List[str] = None,
        confidence_threshold: float = 0.7
    ) -> Tuple[StandardizedDocumentOutput, List[AbbreviationMapping]]:
        """
        Expand abbreviations in a document.

        First pre-scans the document for inline abbreviation definitions
        (e.g., "perovskite solar cells (PSCs)"), then expands subsequent
        occurrences throughout the document.

        Args:
            document: The document to process
            domains: Preferred domains for expansion
            confidence_threshold: Minimum confidence for expansion

        Returns:
            Tuple of (updated_document, expansions_made)
        """
        domains = domains or ['general', 'technical', 'academic', 'document']
        expansions_made = []

        # Pre-scan document for inline abbreviation definitions
        discovered = self._pre_scan_document(document)

        # Create document context
        doc_context = self._create_document_context(document)

        # Process plain text
        expanded_plain_text, plain_expansions = self._expand_text(
            document.plain_text,
            doc_context,
            domains,
            confidence_threshold
        )

        # Process markdown text
        expanded_markdown_text, markdown_expansions = self._expand_text(
            document.markdown_text,
            doc_context,
            domains,
            confidence_threshold
        )

        # Process content elements
        expanded_elements = []
        for element in document.content_elements:
            expanded_content, element_expansions = self._expand_text(
                element.content,
                doc_context,
                domains,
                confidence_threshold
            )

            # Create new element with expanded content
            expanded_element = element.model_copy()
            expanded_element.content = expanded_content
            expanded_elements.append(expanded_element)

            expansions_made.extend(element_expansions)

        # Combine all expansions (include discovered definitions)
        expansions_made.extend(plain_expansions)
        expansions_made.extend(markdown_expansions)
        expansions_made.extend(discovered)

        # Remove duplicates
        unique_expansions = self._deduplicate_expansions(expansions_made)

        # Create updated document
        updated_document = document.model_copy()
        updated_document.content_elements = expanded_elements
        updated_document.plain_text = expanded_plain_text
        updated_document.markdown_text = expanded_markdown_text

        logger.info(f"Expanded {len(unique_expansions)} abbreviations in document "
                     f"({len(discovered)} from pre-scan, {len(unique_expansions) - len(discovered)} from database)")

        return updated_document, unique_expansions
    
    def _create_document_context(self, document: StandardizedDocumentOutput) -> AbbreviationContext:
        """Create context for abbreviation expansion."""
        # Determine document type and domain
        doc_type = "general"
        domain = "general"
        
        # Simple heuristics for domain detection
        text_lower = document.plain_text.lower()
        
        technical_keywords = ['api', 'database', 'algorithm', 'framework', 'implementation']
        academic_keywords = ['research', 'study', 'analysis', 'methodology', 'conclusion']
        business_keywords = ['company', 'revenue', 'market', 'strategy', 'customer']
        
        if any(keyword in text_lower for keyword in technical_keywords):
            domain = "technical"
        elif any(keyword in text_lower for keyword in academic_keywords):
            domain = "academic"
        elif any(keyword in text_lower for keyword in business_keywords):
            domain = "business"
        
        return AbbreviationContext(
            sentence="",
            paragraph="",
            document_type=doc_type,
            domain=domain,
            surrounding_words=[]
        )
    
    def _expand_text(
        self,
        text: str,
        context: AbbreviationContext,
        domains: List[str],
        confidence_threshold: float
    ) -> Tuple[str, List[AbbreviationMapping]]:
        """Expand abbreviations in a text string."""
        if not text:
            return text, []

        # Detect abbreviations
        abbreviations = self.detector.detect_abbreviations(text, context)

        if not abbreviations:
            return text, []

        # Sort by position (reverse order to maintain positions during replacement)
        abbreviations.sort(key=lambda x: x[1], reverse=True)

        expanded_text = text
        expansions_made = []

        for abbrev, start_pos, end_pos in abbreviations:
            # Skip if this occurrence is already part of a definition pattern
            # e.g., "Full Form (ABBREV)" or "ABBREV (Full Form)"
            if self._is_definition_site(expanded_text, abbrev, start_pos, end_pos):
                continue

            # Skip if already expanded (avoid double expansion)
            if self._is_already_expanded(expanded_text, abbrev, start_pos, end_pos):
                continue

            # Get possible expansions
            possible_expansions = []
            for domain in domains:
                possible_expansions.extend(self.database.get_expansions(abbrev, domain))

            if not possible_expansions:
                # Try without domain filter
                possible_expansions = self.database.get_expansions(abbrev)

            if not possible_expansions:
                continue

            # Select best expansion
            best_expansion = self._select_best_expansion(
                abbrev, possible_expansions, context, confidence_threshold
            )

            if best_expansion:
                # Create expansion text
                expansion_text = f"{abbrev} ({best_expansion.expansion})"

                # Replace in text
                expanded_text = (
                    expanded_text[:start_pos] +
                    expansion_text +
                    expanded_text[end_pos:]
                )

                expansions_made.append(best_expansion)

        return expanded_text, expansions_made

    def _is_definition_site(self, text: str, abbrev: str, start_pos: int, end_pos: int) -> bool:
        """
        Check if this abbreviation occurrence is a definition site.

        A definition site is where the abbreviation is being defined,
        e.g., "metal-insulator-semiconductor (MIS)" or "MIS (metal-insulator-semiconductor)".
        We skip these to avoid double-wrapping.
        """
        # Check if abbreviation is inside parentheses (preceded by full form)
        # Pattern: "full form (ABBREV)"
        before = text[max(0, start_pos - 2):start_pos]
        after = text[end_pos:min(len(text), end_pos + 2)]
        if '(' in before and ')' in after:
            return True

        # Check if abbreviation is followed by its expansion in parentheses
        # Pattern: "ABBREV (full form)"
        after_text = text[end_pos:min(len(text), end_pos + 100)]
        if after_text.lstrip().startswith('('):
            paren_content = re.match(r'\s*\(([^)]+)\)', after_text)
            if paren_content:
                content = paren_content.group(1).strip()
                # If the parenthesized content is not all caps and longer than
                # the abbreviation, it's likely a definition (handles both
                # multi-word and single-word expansions like "photoluminescence")
                if not content.isupper() and len(content) > len(abbrev):
                    return True

        return False

    def _is_already_expanded(self, text: str, abbrev: str, start_pos: int, end_pos: int) -> bool:
        """Check if this abbreviation has already been expanded at this position."""
        after_text = text[end_pos:min(len(text), end_pos + 200)]
        # Check for pattern: "ABBREV (expansion)" already present
        if after_text.lstrip().startswith('('):
            return True
        return False
    
    def _select_best_expansion(
        self,
        abbreviation: str,
        expansions: List[AbbreviationMapping],
        context: AbbreviationContext,
        confidence_threshold: float
    ) -> Optional[AbbreviationMapping]:
        """Select the best expansion for an abbreviation."""
        if not expansions:
            return None

        # Filter by confidence threshold
        valid_expansions = [e for e in expansions if e.confidence >= confidence_threshold]

        if not valid_expansions:
            return None

        # Prefer document-scanned definitions (most contextually accurate)
        doc_expansions = [e for e in valid_expansions if e.source == 'document_pre_scan']
        if doc_expansions:
            return max(doc_expansions, key=lambda e: e.confidence)

        # Then prefer domain-specific expansions
        domain_expansions = [e for e in valid_expansions if e.domain == context.domain]
        if domain_expansions:
            return max(domain_expansions, key=lambda e: e.confidence)

        # Fall back to highest confidence
        return max(valid_expansions, key=lambda e: e.confidence)
    
    def _deduplicate_expansions(self, expansions: List[AbbreviationMapping]) -> List[AbbreviationMapping]:
        """Remove duplicate expansions, keeping highest confidence per abbreviation."""
        # Group by abbreviation (case-insensitive)
        abbrev_map: Dict[str, AbbreviationMapping] = {}

        for expansion in expansions:
            key = expansion.abbreviation.upper()
            if key not in abbrev_map:
                abbrev_map[key] = expansion
            elif expansion.confidence > abbrev_map[key].confidence:
                # Keep highest confidence expansion
                abbrev_map[key] = expansion

        return list(abbrev_map.values())
    
    def learn_from_document(self, document: StandardizedDocumentOutput):
        """Learn new abbreviations from a document."""
        # Simple pattern matching for "ABBREV (Full Expansion)" patterns
        text = document.plain_text
        
        # Pattern: "ABBREV (expansion)"
        pattern = re.compile(r'\b([A-Z]{2,5})\s*\(([^)]+)\)')
        
        for match in pattern.finditer(text):
            abbrev = match.group(1)
            expansion = match.group(2).strip()
            
            # Skip if expansion is too short or looks invalid
            if len(expansion) < 3 or expansion.isupper():
                continue
            
            # Determine domain
            context = self._create_document_context(document)
            
            # Create new mapping
            mapping = AbbreviationMapping(
                abbreviation=abbrev,
                expansion=expansion,
                domain=context.domain,
                confidence=0.8,  # Medium confidence for learned abbreviations
                source="document_learning"
            )
            
            self.database.add_abbreviation(mapping)
            logger.info(f"Learned new abbreviation: {abbrev} -> {expansion}")
    
    def get_expansion_statistics(self) -> Dict[str, Any]:
        """Get statistics about abbreviation expansions."""
        all_abbreviations = self.database.get_all_abbreviations()
        
        domain_counts = {}
        confidence_distribution = []
        
        for abbrev in all_abbreviations:
            expansions = self.database.get_expansions(abbrev)
            for expansion in expansions:
                domain_counts[expansion.domain] = domain_counts.get(expansion.domain, 0) + 1
                confidence_distribution.append(expansion.confidence)
        
        avg_confidence = sum(confidence_distribution) / len(confidence_distribution) if confidence_distribution else 0
        
        return {
            "total_abbreviations": len(all_abbreviations),
            "total_expansions": len(confidence_distribution),
            "domain_distribution": domain_counts,
            "average_confidence": avg_confidence,
            "confidence_range": {
                "min": min(confidence_distribution) if confidence_distribution else 0,
                "max": max(confidence_distribution) if confidence_distribution else 0
            }
        }