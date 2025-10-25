"""Post-processing router with Knowledge Management Database."""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime, timezone

from docforge.preprocessing.schemas import StandardizedDocumentOutput, ContentType
from .schemas import (
    ProcessingMethod,
    PostProcessingConfig,
    KnowledgeManagementRule,
    RoutingDecision,
    ChunkingStrategy
)

logger = logging.getLogger(__name__)


class PostProcessKnowledgeManagementDB:
    """Knowledge Management Database for post-processing routing decisions."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the KM database."""
        self.db_path = db_path or "data/postprocess_km.json"
        self.rules: List[KnowledgeManagementRule] = []
        self.decision_history: List[RoutingDecision] = []
        self._load_rules()
    
    def _load_rules(self):
        """Load rules from the KM database."""
        try:
            db_file = Path(self.db_path)
            if db_file.exists():
                with open(db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Load rules
                for rule_data in data.get('rules', []):
                    rule = KnowledgeManagementRule(**rule_data)
                    self.rules.append(rule)
                
                # Load decision history
                for decision_data in data.get('decision_history', []):
                    decision = RoutingDecision(**decision_data)
                    self.decision_history.append(decision)
                    
                logger.info(f"Loaded {len(self.rules)} rules from KM database")
            else:
                # Initialize with default rules
                self._create_default_rules()
                self._save_rules()
                
        except Exception as e:
            logger.error(f"Error loading KM database: {e}")
            self._create_default_rules()
    
    def _create_default_rules(self):
        """Create default post-processing rules."""
        default_rules = [
            KnowledgeManagementRule(
                rule_id="pdf_academic_paper",
                name="Academic Paper Processing",
                description="Process academic papers with section-based chunking and abbreviation expansion",
                conditions={
                    "file_type": "pdf",
                    "has_headings": True,
                    "heading_levels": [1, 2, 3],
                    "min_pages": 3,
                    "keywords": ["abstract", "introduction", "methodology", "results", "conclusion"]
                },
                actions=[
                    ProcessingMethod.SECTION_CHUNKING,
                    ProcessingMethod.ABBREVIATION_EXPANSION
                ],
                priority=10
            ),
            KnowledgeManagementRule(
                rule_id="technical_document",
                name="Technical Document Processing",
                description="Process technical documents with paragraph chunking and abbreviation expansion",
                conditions={
                    "has_technical_terms": True,
                    "has_code_blocks": True,
                    "abbreviation_density": 0.05  # 5% or more abbreviations
                },
                actions=[
                    ProcessingMethod.PARAGRAPH_CHUNKING,
                    ProcessingMethod.ABBREVIATION_EXPANSION
                ],
                priority=8
            ),
            KnowledgeManagementRule(
                rule_id="narrative_text",
                name="Narrative Text Processing",
                description="Process narrative text with sentence-level chunking",
                conditions={
                    "content_type": "narrative",
                    "has_paragraphs": True,
                    "low_heading_density": True
                },
                actions=[
                    ProcessingMethod.SENTENCE_CHUNKING
                ],
                priority=5
            ),
            KnowledgeManagementRule(
                rule_id="structured_document",
                name="Structured Document Processing",
                description="Process structured documents with hierarchical chunking",
                conditions={
                    "has_tables": True,
                    "has_lists": True,
                    "has_headings": True
                },
                actions=[
                    ProcessingMethod.SECTION_CHUNKING,
                    ProcessingMethod.CONTENT_ENHANCEMENT
                ],
                priority=7
            ),
            KnowledgeManagementRule(
                rule_id="default_processing",
                name="Default Processing",
                description="Default processing for all documents",
                conditions={},  # Always matches
                actions=[
                    ProcessingMethod.PARAGRAPH_CHUNKING
                ],
                priority=1
            )
        ]
        
        self.rules = default_rules
    
    def _save_rules(self):
        """Save rules to the KM database."""
        try:
            db_file = Path(self.db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "rules": [rule.model_dump() for rule in self.rules],
                "decision_history": [decision.model_dump() for decision in self.decision_history[-1000:]]  # Keep last 1000 decisions
            }
            
            with open(db_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                
        except Exception as e:
            logger.error(f"Error saving KM database: {e}")
    
    def add_rule(self, rule: KnowledgeManagementRule):
        """Add a new rule to the KM database."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        self._save_rules()
    
    def get_applicable_rules(self, document_features: Dict[str, Any]) -> List[KnowledgeManagementRule]:
        """Get rules that apply to the given document features."""
        applicable_rules = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
                
            if self._rule_matches(rule, document_features):
                applicable_rules.append(rule)
        
        # Sort by priority (highest first)
        applicable_rules.sort(key=lambda r: r.priority, reverse=True)
        return applicable_rules
    
    def _rule_matches(self, rule: KnowledgeManagementRule, features: Dict[str, Any]) -> bool:
        """Check if a rule matches the document features."""
        conditions = rule.conditions
        
        # Empty conditions match everything (default rule)
        if not conditions:
            return True
        
        for condition_key, condition_value in conditions.items():
            feature_value = features.get(condition_key)
            
            if not self._condition_matches(condition_key, condition_value, feature_value):
                return False
        
        return True
    
    def _condition_matches(self, key: str, condition_value: Any, feature_value: Any) -> bool:
        """Check if a specific condition matches."""
        if feature_value is None:
            return False
        
        if isinstance(condition_value, bool):
            return bool(feature_value) == condition_value
        
        elif isinstance(condition_value, (int, float)):
            if key.endswith('_min'):
                return feature_value >= condition_value
            elif key.endswith('_max'):
                return feature_value <= condition_value
            else:
                return feature_value >= condition_value
        
        elif isinstance(condition_value, str):
            if isinstance(feature_value, str):
                return condition_value.lower() in feature_value.lower()
            return str(feature_value).lower() == condition_value.lower()
        
        elif isinstance(condition_value, list):
            if isinstance(feature_value, list):
                return any(item in feature_value for item in condition_value)
            return feature_value in condition_value
        
        return False
    
    def record_decision(self, decision: RoutingDecision):
        """Record a routing decision for learning."""
        self.decision_history.append(decision)
        
        # Keep only recent decisions to prevent unbounded growth
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-1000:]
        
        self._save_rules()


class PostProcessingRouter:
    """Router for post-processing operations with KM DB support."""
    
    def __init__(self, km_db_path: Optional[str] = None):
        """Initialize the post-processing router."""
        self.km_db = PostProcessKnowledgeManagementDB(km_db_path)
        self.feature_extractors = self._initialize_feature_extractors()
    
    def _initialize_feature_extractors(self) -> Dict[str, callable]:
        """Initialize feature extraction functions."""
        return {
            'file_type': self._extract_file_type,
            'has_headings': self._extract_has_headings,
            'heading_levels': self._extract_heading_levels,
            'has_tables': self._extract_has_tables,
            'has_lists': self._extract_has_lists,
            'has_code_blocks': self._extract_has_code_blocks,
            'has_paragraphs': self._extract_has_paragraphs,
            'page_count': self._extract_page_count,
            'word_count': self._extract_word_count,
            'abbreviation_density': self._extract_abbreviation_density,
            'has_technical_terms': self._extract_has_technical_terms,
            'content_type': self._extract_content_type,
            'low_heading_density': self._extract_low_heading_density
        }
    
    def route_document(
        self,
        document: StandardizedDocumentOutput,
        document_id: str,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Tuple[PostProcessingConfig, RoutingDecision]:
        """
        Route a document for post-processing based on KM rules.
        
        Args:
            document: The processed document to route
            document_id: Unique identifier for the document
            user_preferences: Optional user preferences
            
        Returns:
            Tuple of (PostProcessingConfig, RoutingDecision)
        """
        # Extract document features
        features = self._extract_document_features(document)
        
        # Apply user preferences
        if user_preferences:
            features.update(user_preferences)
        
        # Get applicable rules
        applicable_rules = self.km_db.get_applicable_rules(features)
        
        # Determine processing methods
        selected_methods = self._select_processing_methods(applicable_rules, features)
        
        # Create configuration
        config = self._create_processing_config(selected_methods, features)
        
        # Create routing decision
        decision = RoutingDecision(
            document_id=document_id,
            selected_methods=selected_methods,
            applied_rules=[rule.rule_id for rule in applicable_rules],
            confidence=self._calculate_confidence(applicable_rules, features),
            reasoning=self._generate_reasoning(applicable_rules, selected_methods)
        )
        
        # Record decision for learning
        self.km_db.record_decision(decision)
        
        logger.info(f"Routed document {document_id} with methods: {selected_methods}")
        
        return config, decision
    
    def _extract_document_features(self, document: StandardizedDocumentOutput) -> Dict[str, Any]:
        """Extract features from the document for routing decisions."""
        features = {}
        
        for feature_name, extractor in self.feature_extractors.items():
            try:
                features[feature_name] = extractor(document)
            except Exception as e:
                logger.warning(f"Error extracting feature {feature_name}: {e}")
                features[feature_name] = None
        
        return features
    
    def _extract_file_type(self, document: StandardizedDocumentOutput) -> str:
        """Extract file type from document metadata."""
        return document.document_metadata.get('file_extension', '').lower().lstrip('.')
    
    def _extract_has_headings(self, document: StandardizedDocumentOutput) -> bool:
        """Check if document has headings."""
        return any(
            element.content_type == ContentType.HEADING 
            for element in document.content_elements
        )
    
    def _extract_heading_levels(self, document: StandardizedDocumentOutput) -> List[int]:
        """Extract heading levels present in the document."""
        levels = set()
        for element in document.content_elements:
            if element.content_type == ContentType.HEADING:
                level = element.metadata.get('level', 1)
                levels.add(level)
        return sorted(list(levels))
    
    def _extract_has_tables(self, document: StandardizedDocumentOutput) -> bool:
        """Check if document has tables."""
        return len(document.tables) > 0
    
    def _extract_has_lists(self, document: StandardizedDocumentOutput) -> bool:
        """Check if document has lists."""
        return any(
            element.content_type == ContentType.LIST 
            for element in document.content_elements
        )
    
    def _extract_has_code_blocks(self, document: StandardizedDocumentOutput) -> bool:
        """Check if document has code blocks."""
        return any(
            element.content_type == ContentType.CODE 
            for element in document.content_elements
        )
    
    def _extract_has_paragraphs(self, document: StandardizedDocumentOutput) -> bool:
        """Check if document has paragraphs."""
        return any(
            element.content_type == ContentType.PARAGRAPH 
            for element in document.content_elements
        )
    
    def _extract_page_count(self, document: StandardizedDocumentOutput) -> int:
        """Extract page count from document."""
        return document.document_structure.total_pages or 1
    
    def _extract_word_count(self, document: StandardizedDocumentOutput) -> int:
        """Extract word count from document."""
        return len(document.plain_text.split()) if document.plain_text else 0
    
    def _extract_abbreviation_density(self, document: StandardizedDocumentOutput) -> float:
        """Calculate abbreviation density in the document."""
        if not document.plain_text:
            return 0.0
        
        words = document.plain_text.split()
        if not words:
            return 0.0
        
        # Simple heuristic: count words that are all caps and 2-5 characters
        abbreviations = [
            word for word in words 
            if word.isupper() and 2 <= len(word) <= 5 and word.isalpha()
        ]
        
        return len(abbreviations) / len(words)
    
    def _extract_has_technical_terms(self, document: StandardizedDocumentOutput) -> bool:
        """Check if document contains technical terms."""
        if not document.plain_text:
            return False
        
        technical_indicators = [
            'api', 'algorithm', 'database', 'framework', 'implementation',
            'configuration', 'architecture', 'protocol', 'interface', 'specification'
        ]
        
        text_lower = document.plain_text.lower()
        return any(term in text_lower for term in technical_indicators)
    
    def _extract_content_type(self, document: StandardizedDocumentOutput) -> str:
        """Determine the overall content type of the document."""
        element_types = [element.content_type for element in document.content_elements]
        
        if not element_types:
            return "unknown"
        
        # Count element types
        type_counts = {}
        for element_type in element_types:
            type_counts[element_type] = type_counts.get(element_type, 0) + 1
        
        # Determine dominant type
        dominant_type = max(type_counts, key=type_counts.get)
        
        # Classify based on structure
        if ContentType.HEADING in type_counts and type_counts[ContentType.HEADING] > 2:
            return "structured"
        elif ContentType.PARAGRAPH in type_counts and type_counts[ContentType.PARAGRAPH] > len(element_types) * 0.7:
            return "narrative"
        elif ContentType.CODE in type_counts:
            return "technical"
        else:
            return "general"
    
    def _extract_low_heading_density(self, document: StandardizedDocumentOutput) -> bool:
        """Check if document has low heading density."""
        total_elements = len(document.content_elements)
        if total_elements == 0:
            return True
        
        heading_count = sum(
            1 for element in document.content_elements 
            if element.content_type == ContentType.HEADING
        )
        
        heading_density = heading_count / total_elements
        return heading_density < 0.1  # Less than 10% headings
    
    def _select_processing_methods(
        self,
        applicable_rules: List[KnowledgeManagementRule],
        features: Dict[str, Any]
    ) -> List[ProcessingMethod]:
        """Select processing methods based on applicable rules."""
        if not applicable_rules:
            return [ProcessingMethod.PARAGRAPH_CHUNKING]  # Default
        
        # Use the highest priority rule's actions
        primary_rule = applicable_rules[0]
        selected_methods = primary_rule.actions.copy()
        
        # Add methods from other high-priority rules if they don't conflict
        for rule in applicable_rules[1:]:
            if rule.priority >= primary_rule.priority * 0.8:  # Within 20% of top priority
                for method in rule.actions:
                    if method not in selected_methods:
                        selected_methods.append(method)
        
        return selected_methods
    
    def _create_processing_config(
        self,
        methods: List[ProcessingMethod],
        features: Dict[str, Any]
    ) -> PostProcessingConfig:
        """Create post-processing configuration."""
        
        # Determine chunking strategy
        chunking_strategy = None
        if ProcessingMethod.PARAGRAPH_CHUNKING in methods:
            chunking_strategy = ChunkingStrategy.PARAGRAPH
        elif ProcessingMethod.SECTION_CHUNKING in methods:
            chunking_strategy = ChunkingStrategy.SECTION_BASED
        elif ProcessingMethod.SENTENCE_CHUNKING in methods:
            chunking_strategy = ChunkingStrategy.SENTENCE
        elif ProcessingMethod.SEMANTIC_CHUNKING in methods:
            chunking_strategy = ChunkingStrategy.SEMANTIC
        
        # Determine chunk size based on document characteristics
        word_count = features.get('word_count', 1000)
        if word_count < 500:
            chunk_size = 100
        elif word_count < 2000:
            chunk_size = 200
        else:
            chunk_size = 300
        
        return PostProcessingConfig(
            methods=methods,
            chunking_strategy=chunking_strategy,
            chunk_size=chunk_size,
            chunk_overlap=50,  # 50 word overlap
            enable_abbreviation_expansion=ProcessingMethod.ABBREVIATION_EXPANSION in methods,
            abbreviation_domains=self._determine_abbreviation_domains(features),
            language=features.get('language', 'en'),
            quality_threshold=0.8
        )
    
    def _determine_abbreviation_domains(self, features: Dict[str, Any]) -> List[str]:
        """Determine relevant abbreviation domains based on document features."""
        domains = ['general']
        
        if features.get('has_technical_terms'):
            domains.append('technical')
        
        if features.get('file_type') == 'pdf' and features.get('has_headings'):
            domains.append('academic')
        
        content_type = features.get('content_type')
        if content_type == 'technical':
            domains.append('technical')
        elif content_type == 'structured':
            domains.append('business')
        
        return domains
    
    def _calculate_confidence(
        self,
        applicable_rules: List[KnowledgeManagementRule],
        features: Dict[str, Any]
    ) -> float:
        """Calculate confidence in the routing decision."""
        if not applicable_rules:
            return 0.5  # Low confidence for default routing
        
        # Base confidence on rule priority and number of matching conditions
        primary_rule = applicable_rules[0]
        
        # Higher priority rules get higher base confidence
        base_confidence = min(primary_rule.priority / 10.0, 0.9)
        
        # Boost confidence if multiple rules agree
        if len(applicable_rules) > 1:
            base_confidence = min(base_confidence + 0.1, 1.0)
        
        return base_confidence
    
    def _generate_reasoning(
        self,
        applicable_rules: List[KnowledgeManagementRule],
        selected_methods: List[ProcessingMethod]
    ) -> str:
        """Generate human-readable reasoning for the routing decision."""
        if not applicable_rules:
            return "Applied default processing due to no matching rules."
        
        primary_rule = applicable_rules[0]
        reasoning = f"Applied rule '{primary_rule.name}' (priority {primary_rule.priority})"
        
        if len(applicable_rules) > 1:
            other_rules = [rule.name for rule in applicable_rules[1:3]]  # Show up to 2 additional rules
            reasoning += f" and {len(applicable_rules)-1} other rules: {', '.join(other_rules)}"
        
        reasoning += f". Selected methods: {', '.join([method.value for method in selected_methods])}"
        
        return reasoning
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get statistics about post-processing routing decisions."""
        if not self.km_db.decision_history:
            return {"total_decisions": 0}
        
        decisions = self.km_db.decision_history
        
        # Method usage statistics
        method_counts = {}
        for decision in decisions:
            for method in decision.selected_methods:
                method_counts[method.value] = method_counts.get(method.value, 0) + 1
        
        # Rule usage statistics
        rule_counts = {}
        for decision in decisions:
            for rule_id in decision.applied_rules:
                rule_counts[rule_id] = rule_counts.get(rule_id, 0) + 1
        
        # Confidence statistics
        confidences = [decision.confidence for decision in decisions]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "total_decisions": len(decisions),
            "method_usage": method_counts,
            "rule_usage": rule_counts,
            "average_confidence": avg_confidence,
            "total_rules": len(self.km_db.rules),
            "active_rules": len([r for r in self.km_db.rules if r.enabled])
        }