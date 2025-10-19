"""RAG (Retrieval-Augmented Generation) module for document processing and retrieval."""

# Optional imports with graceful fallbacks
try:
    from .lightrag_integration import (
        LightRAGIntegration,
        LightRAGConfig,
        DocumentIndexer,
        VectorRetriever
    )
    LIGHTRAG_INTEGRATION_AVAILABLE = True
except ImportError:
    LIGHTRAG_INTEGRATION_AVAILABLE = False
    LightRAGIntegration = None
    LightRAGConfig = None
    DocumentIndexer = None
    VectorRetriever = None

from .embeddings import EmbeddingManager

try:
    from .indexing import DocumentIndexManager
    INDEXING_AVAILABLE = True
except ImportError:
    INDEXING_AVAILABLE = False
    DocumentIndexManager = None

try:
    from .rag_database_preparation import (
        RAGDatabasePreparation,
        RAGChunkConfig,
        RAGOptimizedChunker,
        SemanticIndexer,
        DocumentRelationshipMapper,
        KnowledgeGraphBuilder,
        DocumentRelationship,
        KnowledgeGraphNode,
        KnowledgeGraphEdge
    )
    RAG_DATABASE_AVAILABLE = True
except ImportError:
    RAG_DATABASE_AVAILABLE = False
    RAGDatabasePreparation = None
    RAGChunkConfig = None
    RAGOptimizedChunker = None
    SemanticIndexer = None
    DocumentRelationshipMapper = None
    KnowledgeGraphBuilder = None
    DocumentRelationship = None
    KnowledgeGraphNode = None
    KnowledgeGraphEdge = None

# Build __all__ dynamically based on available components
__all__ = ['EmbeddingManager']

if LIGHTRAG_INTEGRATION_AVAILABLE:
    __all__.extend([
        'LightRAGIntegration',
        'LightRAGConfig',
        'DocumentIndexer',
        'VectorRetriever'
    ])

if INDEXING_AVAILABLE:
    __all__.append('DocumentIndexManager')

if RAG_DATABASE_AVAILABLE:
    __all__.extend([
        'RAGDatabasePreparation',
        'RAGChunkConfig',
        'RAGOptimizedChunker',
        'SemanticIndexer',
        'DocumentRelationshipMapper',
        'KnowledgeGraphBuilder',
        'DocumentRelationship',
        'KnowledgeGraphNode',
        'KnowledgeGraphEdge'
    ])