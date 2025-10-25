"""RAG database preparation system for optimized retrieval and knowledge graph creation."""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from datetime import datetime, timezone
from pathlib import Path
import uuid
import json
from dataclasses import dataclass, field

# LightRAG imports (optional)
try:
    from lightrag import LightRAG, QueryParam
    from lightrag.utils import EmbeddingFunc
    LIGHTRAG_AVAILABLE = True
except ImportError:
    LightRAG = None
    QueryParam = None
    EmbeddingFunc = None
    LIGHTRAG_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Our imports
from docforge.storage.meta_document_db import MetaDocumentRecord, MetaDocumentComponent
from docforge.storage.meta_document_crud import MetaDocumentCRUD
from .lightrag_integration import LightRAGConfig, LightRAGIntegration
from .embeddings import EmbeddingManager

logger = logging.getLogger(__name__)


@dataclass
class RAGChunkConfig:
    """Configuration for RAG-optimized chunking."""
    chunk_size: int = 512  # Optimal for RAG retrieval
    chunk_overlap: int = 64  # 12.5% overlap
    min_chunk_size: int = 100  # Minimum viable chunk size
    max_chunk_size: int = 1024  # Maximum chunk size
    preserve_sentences: bool = True  # Keep sentences intact
    preserve_paragraphs: bool = True  # Prefer paragraph boundaries
    semantic_similarity_threshold: float = 0.8  # For semantic chunking


@dataclass
class DocumentRelationship:
    """Represents a relationship between documents."""
    source_doc_uuid: str
    target_doc_uuid: str
    relationship_type: str  # 'similar', 'references', 'follows', 'contradicts'
    strength: float  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class KnowledgeGraphNode:
    """Represents a node in the knowledge graph."""
    node_id: str
    node_type: str  # 'document', 'concept', 'entity'
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embeddings: Optional[List[float]] = None


@dataclass
class KnowledgeGraphEdge:
    """Represents an edge in the knowledge graph."""
    source_node_id: str
    target_node_id: str
    edge_type: str  # 'contains', 'references', 'similar_to', 'part_of'
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class RAGOptimizedChunker:
    """Chunker optimized for RAG retrieval performance."""
    
    def __init__(self, config: RAGChunkConfig):
        """Initialize the RAG-optimized chunker."""
        self.config = config
    
    def chunk_meta_document(
        self, 
        meta_doc: MetaDocumentRecord
    ) -> List[Dict[str, Any]]:
        """Chunk a meta document optimized for RAG retrieval."""
        chunks = []
        
        for component in meta_doc.components:
            if not component.content.strip():
                continue
            
            # Chunk based on component type
            if component.component_type == "chunk":
                # Already chunked, but may need re-chunking for RAG optimization
                component_chunks = self._rechunk_for_rag(component.content)
            elif component.component_type == "summary":
                # Keep summaries as single chunks
                component_chunks = [component.content]
            else:
                # Default chunking for other types
                component_chunks = self._chunk_text(component.content)
            
            # Create chunk objects
            for i, chunk_text in enumerate(component_chunks):
                chunk = {
                    'chunk_id': f"{component.component_id}_{i}",
                    'content': chunk_text,
                    'source_component_id': component.component_id,
                    'source_component_type': component.component_type,
                    'meta_doc_uuid': meta_doc.meta_doc_uuid,
                    'doc_uuid': meta_doc.doc_uuid,
                    'set_uuid': meta_doc.set_uuid,
                    'title': meta_doc.title,
                    'chunk_index': i,
                    'total_chunks': len(component_chunks),
                    'metadata': {
                        **component.metadata,
                        'original_order_index': component.order_index,
                        'confidence_score': component.confidence_score,
                        'chunk_size': len(chunk_text),
                        'word_count': len(chunk_text.split())
                    }
                }
                chunks.append(chunk)
        
        return chunks    

    def _rechunk_for_rag(self, text: str) -> List[str]:
        """Re-chunk existing chunks for RAG optimization."""
        # If the chunk is already optimal size, keep it
        if len(text) <= self.config.chunk_size:
            return [text]
        
        # Otherwise, split it optimally
        return self._chunk_text(text)
    
    def _chunk_text(self, text: str) -> List[str]:
        """Chunk text optimally for RAG retrieval."""
        if len(text) <= self.config.chunk_size:
            return [text]
        
        chunks = []
        
        # Try to preserve paragraphs first
        if self.config.preserve_paragraphs:
            paragraphs = text.split('\n\n')
            current_chunk = ""
            
            for paragraph in paragraphs:
                # If adding this paragraph would exceed chunk size
                if len(current_chunk) + len(paragraph) > self.config.chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                        # Start new chunk with overlap
                        overlap_text = self._get_overlap_text(current_chunk)
                        current_chunk = overlap_text + paragraph
                    else:
                        # Paragraph itself is too long, split it
                        para_chunks = self._split_long_paragraph(paragraph)
                        chunks.extend(para_chunks[:-1])
                        current_chunk = para_chunks[-1] if para_chunks else ""
                else:
                    current_chunk += ("\n\n" if current_chunk else "") + paragraph
            
            if current_chunk:
                chunks.append(current_chunk.strip())
        
        # If no chunks created or preserve_paragraphs is False, use sentence-based chunking
        if not chunks:
            chunks = self._chunk_by_sentences(text)
        
        return [chunk for chunk in chunks if len(chunk) >= self.config.min_chunk_size]
    
    def _split_long_paragraph(self, paragraph: str) -> List[str]:
        """Split a long paragraph into smaller chunks."""
        if self.config.preserve_sentences:
            return self._chunk_by_sentences(paragraph)
        else:
            return self._chunk_by_words(paragraph)
    
    def _chunk_by_sentences(self, text: str) -> List[str]:
        """Chunk text by sentences while respecting size limits."""
        import re
        
        # Simple sentence splitting (could be enhanced with NLTK)
        sentences = re.split(r'[.!?]+\s+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # If adding this sentence would exceed chunk size
            if len(current_chunk) + len(sentence) > self.config.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    # Start new chunk with overlap
                    overlap_text = self._get_overlap_text(current_chunk)
                    current_chunk = overlap_text + sentence
                else:
                    # Sentence itself is too long, split by words
                    word_chunks = self._chunk_by_words(sentence)
                    chunks.extend(word_chunks[:-1])
                    current_chunk = word_chunks[-1] if word_chunks else ""
            else:
                current_chunk += (" " if current_chunk else "") + sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _chunk_by_words(self, text: str) -> List[str]:
        """Chunk text by words as a last resort."""
        words = text.split()
        chunks = []
        current_chunk = ""
        
        for word in words:
            # Estimate character count (word + space)
            if len(current_chunk) + len(word) + 1 > self.config.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    # Start new chunk with overlap
                    overlap_words = current_chunk.split()[-self.config.chunk_overlap//10:]
                    current_chunk = " ".join(overlap_words) + " " + word
                else:
                    current_chunk = word
            else:
                current_chunk += (" " if current_chunk else "") + word
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text for the next chunk."""
        if len(text) <= self.config.chunk_overlap:
            return text + " "
        
        # Get last N characters for overlap
        overlap = text[-self.config.chunk_overlap:].strip()
        
        # Try to start overlap at word boundary
        space_index = overlap.find(' ')
        if space_index > 0:
            overlap = overlap[space_index:].strip()
        
        return overlap + " " if overlap else ""


class SemanticIndexer:
    """Handles semantic indexing for improved RAG retrieval."""
    
    def __init__(
        self, 
        embedding_manager: EmbeddingManager,
        similarity_threshold: float = 0.8
    ):
        """Initialize the semantic indexer."""
        self.embedding_manager = embedding_manager
        self.similarity_threshold = similarity_threshold
    
    async def create_semantic_index(
        self, 
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create semantic index for chunks."""
        try:
            # Generate embeddings for all chunks
            chunk_texts = [chunk['content'] for chunk in chunks]
            embeddings = await self.embedding_manager.embed_texts(chunk_texts)
            
            # Add embeddings to chunks
            for i, chunk in enumerate(chunks):
                chunk['embedding'] = embeddings[i]
            
            # Create semantic clusters
            clusters = self._create_semantic_clusters(chunks, embeddings)
            
            # Create semantic relationships
            relationships = self._create_semantic_relationships(chunks, embeddings)
            
            return {
                'indexed_chunks': chunks,
                'semantic_clusters': clusters,
                'semantic_relationships': relationships,
                'total_chunks': len(chunks),
                'total_clusters': len(clusters),
                'total_relationships': len(relationships),
                'indexed_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create semantic index: {e}")
            raise
    
    def _create_semantic_clusters(
        self, 
        chunks: List[Dict[str, Any]], 
        embeddings: List[List[float]]
    ) -> List[Dict[str, Any]]:
        """Create semantic clusters of similar chunks."""
        clusters = []
        used_chunks = set()
        
        for i, chunk in enumerate(chunks):
            if i in used_chunks:
                continue
            
            # Find similar chunks
            similar_chunks = [i]  # Start with current chunk
            
            for j, other_chunk in enumerate(chunks):
                if i != j and j not in used_chunks:
                    similarity = self.embedding_manager.calculate_similarity(
                        embeddings[i], 
                        embeddings[j]
                    )
                    
                    if similarity >= self.similarity_threshold:
                        similar_chunks.append(j)
            
            # Create cluster if we have multiple similar chunks
            if len(similar_chunks) > 1:
                cluster = {
                    'cluster_id': str(uuid.uuid4()),
                    'chunk_indices': similar_chunks,
                    'chunk_ids': [chunks[idx]['chunk_id'] for idx in similar_chunks],
                    'representative_chunk_id': chunks[i]['chunk_id'],
                    'cluster_size': len(similar_chunks),
                    'average_similarity': self._calculate_average_similarity(
                        [embeddings[idx] for idx in similar_chunks]
                    ),
                    'topics': self._extract_cluster_topics(
                        [chunks[idx]['content'] for idx in similar_chunks]
                    )
                }
                clusters.append(cluster)
                
                # Mark chunks as used
                used_chunks.update(similar_chunks)
        
        return clusters
    
    def _create_semantic_relationships(
        self, 
        chunks: List[Dict[str, Any]], 
        embeddings: List[List[float]]
    ) -> List[Dict[str, Any]]:
        """Create semantic relationships between chunks."""
        relationships = []
        
        for i, chunk in enumerate(chunks):
            # Find top similar chunks
            similarities = []
            
            for j, other_chunk in enumerate(chunks):
                if i != j:
                    similarity = self.embedding_manager.calculate_similarity(
                        embeddings[i], 
                        embeddings[j]
                    )
                    similarities.append((j, similarity))
            
            # Sort by similarity and take top relationships
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_similarities = similarities[:5]  # Top 5 most similar
            
            for j, similarity in top_similarities:
                if similarity >= self.similarity_threshold:
                    relationship = {
                        'relationship_id': str(uuid.uuid4()),
                        'source_chunk_id': chunk['chunk_id'],
                        'target_chunk_id': chunks[j]['chunk_id'],
                        'relationship_type': 'semantic_similarity',
                        'strength': similarity,
                        'metadata': {
                            'source_doc_uuid': chunk['doc_uuid'],
                            'target_doc_uuid': chunks[j]['doc_uuid'],
                            'cross_document': chunk['doc_uuid'] != chunks[j]['doc_uuid']
                        }
                    }
                    relationships.append(relationship)
        
        return relationships
    
    def _calculate_average_similarity(self, embeddings: List[List[float]]) -> float:
        """Calculate average similarity within a cluster."""
        if len(embeddings) < 2:
            return 1.0
        
        total_similarity = 0.0
        comparisons = 0
        
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                similarity = self.embedding_manager.calculate_similarity(
                    embeddings[i], 
                    embeddings[j]
                )
                total_similarity += similarity
                comparisons += 1
        
        return total_similarity / comparisons if comparisons > 0 else 0.0
    
    def _extract_cluster_topics(self, texts: List[str]) -> List[str]:
        """Extract topics from a cluster of texts."""
        # Simple keyword extraction (could be enhanced with NLP libraries)
        from collections import Counter
        import re
        
        # Combine all texts
        combined_text = " ".join(texts).lower()
        
        # Extract words (simple approach)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', combined_text)
        
        # Remove common stop words
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'among', 'this', 'that', 'these',
            'those', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'
        }
        
        filtered_words = [word for word in words if word not in stop_words]
        
        # Get most common words as topics
        word_counts = Counter(filtered_words)
        topics = [word for word, count in word_counts.most_common(10) if count > 1]
        
        return topics[:5]  # Return top 5 topics


class DocumentRelationshipMapper:
    """Maps relationships between documents for context retrieval."""
    
    def __init__(self, embedding_manager: EmbeddingManager):
        """Initialize the document relationship mapper."""
        self.embedding_manager = embedding_manager
    
    async def map_document_relationships(
        self, 
        meta_docs: List[MetaDocumentRecord]
    ) -> List[DocumentRelationship]:
        """Map relationships between meta documents."""
        relationships = []
        
        if len(meta_docs) < 2:
            return relationships
        
        # Generate document-level embeddings (summary + title)
        doc_embeddings = await self._generate_document_embeddings(meta_docs)
        
        # Create relationships based on similarity
        for i, doc1 in enumerate(meta_docs):
            for j, doc2 in enumerate(meta_docs):
                if i >= j:  # Avoid duplicates and self-relationships
                    continue
                
                similarity = self.embedding_manager.calculate_similarity(
                    doc_embeddings[i], 
                    doc_embeddings[j]
                )
                
                # Create relationship if similarity is high enough
                if similarity >= 0.5:  # Adjusted threshold for better document relationship detection
                    relationship_type = self._determine_relationship_type(
                        doc1, doc2, similarity
                    )
                    
                    relationship = DocumentRelationship(
                        source_doc_uuid=doc1.meta_doc_uuid,
                        target_doc_uuid=doc2.meta_doc_uuid,
                        relationship_type=relationship_type,
                        strength=similarity,
                        metadata={
                            'source_title': doc1.title,
                            'target_title': doc2.title,
                            'source_doc_uuid': doc1.doc_uuid,
                            'target_doc_uuid': doc2.doc_uuid,
                            'similarity_score': similarity
                        }
                    )
                    relationships.append(relationship)
        
        # Add temporal relationships (if documents are from same source)
        temporal_relationships = self._create_temporal_relationships(meta_docs)
        relationships.extend(temporal_relationships)
        
        return relationships
    
    async def _generate_document_embeddings(
        self, 
        meta_docs: List[MetaDocumentRecord]
    ) -> List[List[float]]:
        """Generate embeddings for documents based on title and summary."""
        doc_texts = []
        
        for doc in meta_docs:
            # Combine title and summary for document representation
            doc_text = f"Title: {doc.title}\n\nSummary: {doc.summary}"
            
            # Add key content from components with better selection
            key_content = []
            summary_components = [c for c in doc.components if c.component_type == 'summary']
            chunk_components = [c for c in doc.components if c.component_type == 'chunk']
            
            # Prioritize summary components
            for component in summary_components[:2]:
                key_content.append(component.content[:300])
            
            # Add high-confidence chunks
            high_conf_chunks = [c for c in chunk_components if c.confidence_score > 0.7]
            for component in high_conf_chunks[:3]:
                key_content.append(component.content[:200])
            
            if key_content:
                doc_text += "\n\nKey Content:\n" + "\n\n".join(key_content)
            
            doc_texts.append(doc_text)
        
        return await self.embedding_manager.embed_texts(doc_texts)
    
    def _determine_relationship_type(
        self, 
        doc1: MetaDocumentRecord, 
        doc2: MetaDocumentRecord, 
        similarity: float
    ) -> str:
        """Determine the type of relationship between documents."""
        # Check if documents are from the same source
        if doc1.doc_uuid == doc2.doc_uuid:
            return "version_of"  # Different processing versions
        
        # Check temporal relationship
        time_diff = abs((doc1.created_at - doc2.created_at).total_seconds())
        if time_diff < 3600:  # Within 1 hour
            return "concurrent"
        
        # Based on similarity strength (adjusted thresholds for better detection)
        if similarity >= 0.85:
            return "duplicate"
        elif similarity >= 0.7:
            return "similar"
        elif similarity >= 0.5:
            return "related"
        else:
            return "weak_relation"
    
    async def test_relationship_detection(
        self, 
        meta_docs: List[MetaDocumentRecord]
    ) -> Dict[str, Any]:
        """Test document relationship detection with detailed metrics."""
        test_results = {
            'total_documents': len(meta_docs),
            'relationships_found': 0,
            'relationship_types': {},
            'similarity_distribution': [],
            'processing_time': 0,
            'errors': []
        }
        
        try:
            import time
            start_time = time.time()
            
            # Map relationships
            relationships = await self.map_document_relationships(meta_docs)
            
            test_results['relationships_found'] = len(relationships)
            test_results['processing_time'] = time.time() - start_time
            
            # Analyze relationship types
            for rel in relationships:
                rel_type = rel.relationship_type
                if rel_type not in test_results['relationship_types']:
                    test_results['relationship_types'][rel_type] = 0
                test_results['relationship_types'][rel_type] += 1
                
                # Collect similarity scores
                test_results['similarity_distribution'].append({
                    'type': rel_type,
                    'strength': rel.strength,
                    'source_title': rel.metadata.get('source_title', 'Unknown'),
                    'target_title': rel.metadata.get('target_title', 'Unknown')
                })
            
            # Calculate statistics
            if test_results['similarity_distribution']:
                similarities = [r['strength'] for r in test_results['similarity_distribution']]
                test_results['similarity_stats'] = {
                    'min': min(similarities),
                    'max': max(similarities),
                    'avg': sum(similarities) / len(similarities),
                    'count': len(similarities)
                }
            
        except Exception as e:
            test_results['errors'].append(f"Relationship detection test failed: {e}")
        
        return test_results
    
    def _create_temporal_relationships(
        self, 
        meta_docs: List[MetaDocumentRecord]
    ) -> List[DocumentRelationship]:
        """Create temporal relationships between documents."""
        relationships = []
        
        # Group documents by source document UUID
        doc_groups = {}
        for doc in meta_docs:
            if doc.doc_uuid not in doc_groups:
                doc_groups[doc.doc_uuid] = []
            doc_groups[doc.doc_uuid].append(doc)
        
        # Create temporal relationships within each group
        for doc_uuid, docs in doc_groups.items():
            if len(docs) < 2:
                continue
            
            # Sort by creation time
            docs.sort(key=lambda x: x.created_at)
            
            # Create "follows" relationships
            for i in range(len(docs) - 1):
                relationship = DocumentRelationship(
                    source_doc_uuid=docs[i].meta_doc_uuid,
                    target_doc_uuid=docs[i + 1].meta_doc_uuid,
                    relationship_type="follows",
                    strength=1.0,  # Temporal relationships are certain
                    metadata={
                        'temporal_order': i,
                        'time_difference': (docs[i + 1].created_at - docs[i].created_at).total_seconds(),
                        'source_set_uuid': docs[i].set_uuid,
                        'target_set_uuid': docs[i + 1].set_uuid
                    }
                )
                relationships.append(relationship)
        
        return relationships


class KnowledgeGraphBuilder:
    """Builds knowledge graphs from processed documents using LightRAG."""
    
    def __init__(
        self, 
        lightrag_integration: LightRAGIntegration,
        embedding_manager: EmbeddingManager
    ):
        """Initialize the knowledge graph builder."""
        self.lightrag_integration = lightrag_integration
        self.embedding_manager = embedding_manager
    
    async def build_knowledge_graph(
        self, 
        meta_docs: List[MetaDocumentRecord],
        relationships: List[DocumentRelationship]
    ) -> Dict[str, Any]:
        """Build a knowledge graph from meta documents and relationships."""
        try:
            # Create nodes from documents and components
            nodes = await self._create_graph_nodes(meta_docs)
            
            # Create edges from relationships and semantic connections
            edges = await self._create_graph_edges(meta_docs, relationships)
            
            # Index everything in LightRAG for graph-based retrieval
            await self._index_knowledge_graph(nodes, edges)
            
            # Create graph statistics
            stats = self._calculate_graph_statistics(nodes, edges)
            
            return {
                'nodes': nodes,
                'edges': edges,
                'statistics': stats,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to build knowledge graph: {e}")
            raise
    
    async def _create_graph_nodes(
        self, 
        meta_docs: List[MetaDocumentRecord]
    ) -> List[KnowledgeGraphNode]:
        """Create nodes for the knowledge graph."""
        nodes = []
        
        for doc in meta_docs:
            # Create document node
            doc_node = KnowledgeGraphNode(
                node_id=f"doc_{doc.meta_doc_uuid}",
                node_type="document",
                content=f"{doc.title}\n\n{doc.summary}",
                metadata={
                    'meta_doc_uuid': doc.meta_doc_uuid,
                    'doc_uuid': doc.doc_uuid,
                    'set_uuid': doc.set_uuid,
                    'title': doc.title,
                    'component_count': len(doc.components),
                    'created_at': doc.created_at.isoformat()
                }
            )
            nodes.append(doc_node)
            
            # Create component nodes
            for component in doc.components:
                if component.content.strip():
                    comp_node = KnowledgeGraphNode(
                        node_id=f"comp_{component.component_id}",
                        node_type="component",
                        content=component.content,
                        metadata={
                            'component_id': component.component_id,
                            'component_type': component.component_type,
                            'parent_doc_uuid': doc.meta_doc_uuid,
                            'order_index': component.order_index,
                            'confidence_score': component.confidence_score,
                            **component.metadata
                        }
                    )
                    nodes.append(comp_node)
        
        # Generate embeddings for all nodes
        node_texts = [node.content for node in nodes]
        embeddings = await self.embedding_manager.embed_texts(node_texts)
        
        for i, node in enumerate(nodes):
            node.embeddings = embeddings[i]
        
        return nodes
    
    async def _create_graph_edges(
        self, 
        meta_docs: List[MetaDocumentRecord],
        relationships: List[DocumentRelationship]
    ) -> List[KnowledgeGraphEdge]:
        """Create edges for the knowledge graph."""
        edges = []
        
        # Create document-to-component edges
        for doc in meta_docs:
            doc_node_id = f"doc_{doc.meta_doc_uuid}"
            
            for component in doc.components:
                comp_node_id = f"comp_{component.component_id}"
                
                edge = KnowledgeGraphEdge(
                    source_node_id=doc_node_id,
                    target_node_id=comp_node_id,
                    edge_type="contains",
                    weight=1.0,
                    metadata={
                        'component_type': component.component_type,
                        'order_index': component.order_index
                    }
                )
                edges.append(edge)
        
        # Create edges from document relationships
        for relationship in relationships:
            source_node_id = f"doc_{relationship.source_doc_uuid}"
            target_node_id = f"doc_{relationship.target_doc_uuid}"
            
            edge = KnowledgeGraphEdge(
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                edge_type=relationship.relationship_type,
                weight=relationship.strength,
                metadata=relationship.metadata
            )
            edges.append(edge)
        
        return edges
    
    async def _index_knowledge_graph(
        self, 
        nodes: List[KnowledgeGraphNode], 
        edges: List[KnowledgeGraphEdge]
    ):
        """Index the knowledge graph in LightRAG."""
        try:
            # Ensure LightRAG is properly initialized
            await self.lightrag_integration.indexer._ensure_initialized()
            
            # Create a comprehensive text representation of the knowledge graph
            graph_text = self._create_graph_text_representation(nodes, edges)
            
            # Index in LightRAG
            await self.lightrag_integration.indexer.lightrag.ainsert(graph_text)
            
            logger.info(f"Indexed knowledge graph with {len(nodes)} nodes and {len(edges)} edges")
            
        except Exception as e:
            logger.error(f"Failed to index knowledge graph: {e}")
            raise
    
    def _create_graph_text_representation(
        self, 
        nodes: List[KnowledgeGraphNode], 
        edges: List[KnowledgeGraphEdge]
    ) -> str:
        """Create a text representation of the knowledge graph for LightRAG."""
        text_parts = []
        
        # Add document nodes
        doc_nodes = [node for node in nodes if node.node_type == "document"]
        for node in doc_nodes:
            text_parts.append(f"DOCUMENT: {node.content}")
        
        # Add relationships
        text_parts.append("\nRELATIONSHIPS:")
        for edge in edges:
            if edge.edge_type in ["similar", "related", "follows"]:
                source_node = next((n for n in nodes if n.node_id == edge.source_node_id), None)
                target_node = next((n for n in nodes if n.node_id == edge.target_node_id), None)
                
                if source_node and target_node:
                    text_parts.append(
                        f"{source_node.metadata.get('title', 'Document')} "
                        f"{edge.edge_type} "
                        f"{target_node.metadata.get('title', 'Document')}"
                    )
        
        return "\n\n".join(text_parts)
    
    def _calculate_graph_statistics(
        self, 
        nodes: List[KnowledgeGraphNode], 
        edges: List[KnowledgeGraphEdge]
    ) -> Dict[str, Any]:
        """Calculate statistics for the knowledge graph."""
        node_types = {}
        edge_types = {}
        
        for node in nodes:
            node_types[node.node_type] = node_types.get(node.node_type, 0) + 1
        
        for edge in edges:
            edge_types[edge.edge_type] = edge_types.get(edge.edge_type, 0) + 1
        
        return {
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'node_types': node_types,
            'edge_types': edge_types,
            'average_edges_per_node': len(edges) / len(nodes) if nodes else 0,
            'graph_density': len(edges) / (len(nodes) * (len(nodes) - 1) / 2) if len(nodes) > 1 else 0
        }


class RAGDatabasePreparation:
    """Main class for RAG database preparation and optimization."""
    
    def __init__(
        self,
        lightrag_integration: LightRAGIntegration,
        meta_doc_crud: Optional[MetaDocumentCRUD] = None,
        chunk_config: Optional[RAGChunkConfig] = None
    ):
        """Initialize RAG database preparation."""
        self.lightrag_integration = lightrag_integration
        self.meta_doc_crud = meta_doc_crud or MetaDocumentCRUD()
        self.chunk_config = chunk_config or RAGChunkConfig()
        
        # Initialize components
        self.chunker = RAGOptimizedChunker(self.chunk_config)
        
        # Create embedding manager for semantic operations
        embedding_manager = EmbeddingManager(
            model_name=lightrag_integration.config.embedding_model,
            batch_size=lightrag_integration.config.batch_size
        )
        
        self.semantic_indexer = SemanticIndexer(
            embedding_manager,
            self.chunk_config.semantic_similarity_threshold
        )
        self.relationship_mapper = DocumentRelationshipMapper(embedding_manager)
        self.knowledge_graph_builder = KnowledgeGraphBuilder(
            lightrag_integration,
            embedding_manager
        )
    
    async def prepare_documents_for_rag(
        self, 
        meta_doc_uuids: List[str],
        include_knowledge_graph: bool = True
    ) -> Dict[str, Any]:
        """Prepare multiple documents for RAG retrieval."""
        try:
            logger.info(f"Starting RAG preparation for {len(meta_doc_uuids)} documents: {meta_doc_uuids}")
            logger.info(f"Using MetaDocumentCRUD with database: {getattr(self.meta_doc_crud, 'db_path', 'unknown')}")
            
            # Get meta documents
            meta_docs = []
            for uuid in meta_doc_uuids:
                logger.debug(f"Attempting to retrieve meta document: {uuid}")
                doc = self.meta_doc_crud.get_meta_document(uuid)
                if doc:
                    logger.info(f"✓ Successfully retrieved meta document: {uuid} (title: {doc.title})")
                    meta_docs.append(doc)
                else:
                    logger.warning(f"✗ Failed to retrieve meta document: {uuid}")
            
            logger.info(f"Retrieved {len(meta_docs)} out of {len(meta_doc_uuids)} requested documents")
            
            if not meta_docs:
                logger.error("No valid meta documents found - this indicates a database connection issue")
                raise ValueError("No valid meta documents found")
            
            # Step 1: Chunk documents optimally for RAG
            all_chunks = []
            for doc in meta_docs:
                chunks = self.chunker.chunk_meta_document(doc)
                all_chunks.extend(chunks)
            
            # Step 2: Create semantic index
            semantic_index = await self.semantic_indexer.create_semantic_index(all_chunks)
            
            # Step 3: Map document relationships
            relationships = await self.relationship_mapper.map_document_relationships(meta_docs)
            
            # Step 4: Store relationships in meta document database
            await self._store_relationships(relationships)
            
            # Step 5: Build knowledge graph (optional)
            knowledge_graph = None
            if include_knowledge_graph:
                knowledge_graph = await self.knowledge_graph_builder.build_knowledge_graph(
                    meta_docs, relationships
                )
            
            # Step 6: Index everything in LightRAG
            indexing_results = await self._index_prepared_data(
                meta_docs, all_chunks, relationships, knowledge_graph
            )
            
            # Step 7: Update RAG preparation status
            await self._update_rag_status(meta_doc_uuids, indexing_results)
            
            return {
                'meta_documents': len(meta_docs),
                'total_chunks': len(all_chunks),
                'semantic_index': semantic_index,
                'relationships': len(relationships),
                'knowledge_graph': knowledge_graph,
                'indexing_results': indexing_results,
                'prepared_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to prepare documents for RAG: {e}")
            # Update status with error
            for uuid in meta_doc_uuids:
                self.meta_doc_crud.update_rag_preparation_status(
                    uuid, "rag_preparation", "failed", error_message=str(e)
                )
            raise
    
    async def _store_relationships(self, relationships: List[DocumentRelationship]):
        """Store document relationships in the database."""
        for relationship in relationships:
            try:
                self.meta_doc_crud.create_document_relationship(
                    source_meta_doc_uuid=relationship.source_doc_uuid,
                    target_meta_doc_uuid=relationship.target_doc_uuid,
                    relationship_type=relationship.relationship_type,
                    relationship_strength=relationship.strength,
                    metadata=relationship.metadata
                )
            except Exception as e:
                logger.warning(f"Failed to store relationship: {e}")
    
    async def _index_prepared_data(
        self,
        meta_docs: List[MetaDocumentRecord],
        chunks: List[Dict[str, Any]],
        relationships: List[DocumentRelationship],
        knowledge_graph: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Index all prepared data in LightRAG."""
        indexing_results = {
            'documents_indexed': 0,
            'chunks_indexed': 0,
            'relationships_indexed': 0,
            'knowledge_graph_indexed': False,
            'errors': []
        }
        
        try:
            # Index each meta document
            for doc in meta_docs:
                try:
                    result = await self.lightrag_integration.prepare_document_for_rag(
                        doc.meta_doc_uuid
                    )
                    if result['status'] == 'completed':
                        indexing_results['documents_indexed'] += 1
                    else:
                        indexing_results['errors'].append(f"Failed to index {doc.meta_doc_uuid}")
                except Exception as e:
                    indexing_results['errors'].append(f"Error indexing {doc.meta_doc_uuid}: {e}")
            
            # Ensure LightRAG is properly initialized before indexing
            await self.lightrag_integration.indexer._ensure_initialized()
            
            # Index chunk-level information
            chunk_text = self._create_chunk_summary_text(chunks)
            if chunk_text:
                await self.lightrag_integration.indexer.lightrag.ainsert(chunk_text)
                indexing_results['chunks_indexed'] = len(chunks)
            
            # Index relationship information
            relationship_text = self._create_relationship_text(relationships)
            if relationship_text:
                await self.lightrag_integration.indexer.lightrag.ainsert(relationship_text)
                indexing_results['relationships_indexed'] = len(relationships)
            
            # Knowledge graph is already indexed in the builder
            if knowledge_graph:
                indexing_results['knowledge_graph_indexed'] = True
            
        except Exception as e:
            logger.error(f"Error during indexing: {e}")
            indexing_results['errors'].append(str(e))
        
        return indexing_results
    
    def _create_chunk_summary_text(self, chunks: List[Dict[str, Any]]) -> str:
        """Create summary text from chunks for indexing."""
        if not chunks:
            return ""
        
        # Group chunks by document
        doc_chunks = {}
        for chunk in chunks:
            doc_uuid = chunk['meta_doc_uuid']
            if doc_uuid not in doc_chunks:
                doc_chunks[doc_uuid] = []
            doc_chunks[doc_uuid].append(chunk)
        
        text_parts = []
        for doc_uuid, doc_chunks_list in doc_chunks.items():
            title = doc_chunks_list[0].get('title', 'Unknown Document')
            chunk_count = len(doc_chunks_list)
            
            text_parts.append(
                f"Document '{title}' contains {chunk_count} chunks covering various topics."
            )
        
        return "\n".join(text_parts)
    
    def _create_relationship_text(self, relationships: List[DocumentRelationship]) -> str:
        """Create text representation of relationships for indexing."""
        if not relationships:
            return ""
        
        text_parts = ["DOCUMENT RELATIONSHIPS:"]
        
        for rel in relationships:
            source_title = rel.metadata.get('source_title', 'Document')
            target_title = rel.metadata.get('target_title', 'Document')
            
            text_parts.append(
                f"{source_title} {rel.relationship_type} {target_title} "
                f"(strength: {rel.strength:.2f})"
            )
        
        return "\n".join(text_parts)
    
    async def _update_rag_status(
        self, 
        meta_doc_uuids: List[str], 
        indexing_results: Dict[str, Any]
    ):
        """Update RAG preparation status for all documents."""
        for uuid in meta_doc_uuids:
            try:
                if indexing_results['documents_indexed'] > 0:
                    # Mark as completed
                    self.meta_doc_crud.update_rag_preparation_status(
                        uuid, "rag_preparation", "completed", progress_percentage=100.0
                    )
                    
                    # Mark as RAG ready
                    self.meta_doc_crud.update_rag_ready_status(
                        uuid, True, 
                        vector_index_id=f"lightrag_{uuid}",
                        knowledge_graph_id=f"kg_{uuid}"
                    )
                else:
                    # Mark as failed
                    error_msg = "; ".join(indexing_results.get('errors', ['Unknown error']))
                    self.meta_doc_crud.update_rag_preparation_status(
                        uuid, "rag_preparation", "failed", error_message=error_msg
                    )
            except Exception as e:
                logger.error(f"Failed to update RAG status for {uuid}: {e}")
    
    async def query_prepared_documents(
        self, 
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        include_relationships: bool = True
    ) -> Dict[str, Any]:
        """Query the prepared RAG database."""
        try:
            # Query using LightRAG
            results = await self.lightrag_integration.query_documents(
                query=query,
                filters=filters,
                include_metadata=True
            )
            
            # Enhance with relationship information if requested
            if include_relationships and results.get('results'):
                enhanced_results = await self._enhance_with_relationships(
                    results['results']
                )
                results['results'] = enhanced_results
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to query prepared documents: {e}")
            return {
                'query': query,
                'results': [],
                'error': str(e),
                'retrieved_at': datetime.now(timezone.utc).isoformat()
            }
    
    async def _enhance_with_relationships(
        self, 
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Enhance query results with relationship information."""
        enhanced_results = []
        
        for result in results:
            enhanced_result = result.copy()
            
            # Get document UUID from metadata
            meta_doc_uuid = result.get('metadata', {}).get('meta_doc_uuid')
            
            if meta_doc_uuid:
                # Get relationships for this document
                relationships = self.meta_doc_crud.get_document_relationships(meta_doc_uuid)
                enhanced_result['relationships'] = relationships
            
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
    
    def get_preparation_statistics(self) -> Dict[str, Any]:
        """Get statistics about RAG preparation."""
        try:
            # Get meta document statistics
            meta_stats = self.meta_doc_crud.get_statistics()
            
            # Get LightRAG statistics
            rag_stats = self.lightrag_integration.get_rag_statistics()
            
            return {
                'meta_document_stats': meta_stats,
                'lightrag_stats': rag_stats,
                'chunk_config': {
                    'chunk_size': self.chunk_config.chunk_size,
                    'chunk_overlap': self.chunk_config.chunk_overlap,
                    'semantic_threshold': self.chunk_config.semantic_similarity_threshold
                },
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get preparation statistics: {e}")
            return {'error': str(e)}