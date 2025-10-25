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
            
            # Mixed case abbreviations (e.g., PhD, MSc, BSc)
            re.compile(r'\b[A-Z][a-z]*[A-Z][a-z]*\b'),
            
            # Academic degrees (e.g., PhD, MSc, BSc)
            re.compile(r'\b[A-Z][a-z]?[A-Z]\b'),
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
    
    def expand_abbreviations(
        self,
        document: StandardizedDocumentOutput,
        domains: List[str] = None,
        confidence_threshold: float = 0.7
    ) -> Tuple[StandardizedDocumentOutput, List[AbbreviationMapping]]:
        """
        Expand abbreviations in a document.
        
        Args:
            document: The document to process
            domains: Preferred domains for expansion
            confidence_threshold: Minimum confidence for expansion
            
        Returns:
            Tuple of (updated_document, expansions_made)
        """
        domains = domains or ['general', 'technical', 'academic']
        expansions_made = []
        
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
        
        # Combine all expansions
        expansions_made.extend(plain_expansions)
        expansions_made.extend(markdown_expansions)
        
        # Remove duplicates
        unique_expansions = self._deduplicate_expansions(expansions_made)
        
        # Create updated document
        updated_document = document.model_copy()
        updated_document.content_elements = expanded_elements
        updated_document.plain_text = expanded_plain_text
        updated_document.markdown_text = expanded_markdown_text
        
        logger.info(f"Expanded {len(unique_expansions)} abbreviations in document")
        
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
        
        # Prefer domain-specific expansions
        domain_expansions = [e for e in valid_expansions if e.domain == context.domain]
        if domain_expansions:
            return max(domain_expansions, key=lambda e: e.confidence)
        
        # Fall back to highest confidence
        return max(valid_expansions, key=lambda e: e.confidence)
    
    def _deduplicate_expansions(self, expansions: List[AbbreviationMapping]) -> List[AbbreviationMapping]:
        """Remove duplicate expansions."""
        seen = set()
        unique_expansions = []
        
        for expansion in expansions:
            key = (expansion.abbreviation, expansion.expansion, expansion.domain)
            if key not in seen:
                seen.add(key)
                unique_expansions.append(expansion)
        
        return unique_expansions
    
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