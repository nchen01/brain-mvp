"""Embedding management for document processing."""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timezone
import numpy as np
from pathlib import Path
import pickle
import json

# Sentence Transformers for embeddings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manages embeddings for documents and components."""
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        cache_dir: str = "data/embeddings_cache",
        batch_size: int = 32,
        max_workers: int = 4,
        max_cache_size: int = 10000,
        cache_save_interval: int = 100
    ):
        """Initialize the embedding manager."""
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.max_cache_size = max_cache_size
        self.cache_save_interval = cache_save_interval
        
        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize embedder
        self.embedder = None
        self.batch_embedder = None
        self._setup_embedder()
        
        # Cache for embeddings
        self._embedding_cache = {}
        self._cache_hits = 0
        self._cache_requests = 0
        self._cache_additions = 0
        self._load_cache()
    
    def _setup_embedder(self):
        """Set up the embedder components."""
        try:
            # Initialize sentence transformer model with optimizations
            import torch
            device = 'cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu'
            
            self.embedder = SentenceTransformer(self.model_name, device=device)
            
            # Get embedding dimension
            self.embedding_dim = self.embedder.get_sentence_embedding_dimension()
            
            logger.info(f"Embedder initialized with model: {self.model_name} on device: {device}")
            logger.info(f"Embedding dimension: {self.embedding_dim}")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedder: {e}")
            raise
    
    def _load_cache(self):
        """Load embedding cache from disk."""
        cache_file = self.cache_dir / "embedding_cache.pkl"
        
        try:
            if cache_file.exists():
                # Use builtins.open to avoid any potential shadowing issues
                import builtins
                with builtins.open(cache_file, 'rb') as f:
                    self._embedding_cache = pickle.load(f)
                logger.info(f"Loaded {len(self._embedding_cache)} cached embeddings")
            else:
                self._embedding_cache = {}
                logger.debug(f"No cache file found at {cache_file}, starting with empty cache")
        except (FileNotFoundError, EOFError) as e:
            logger.info(f"Cache file not found or empty, starting fresh: {e}")
            self._embedding_cache = {}
        except (pickle.PickleError, pickle.UnpicklingError) as e:
            logger.warning(f"Corrupted cache file, starting fresh: {e}")
            self._embedding_cache = {}
            # Try to backup the corrupted file
            try:
                backup_file = cache_file.with_suffix('.pkl.corrupted')
                cache_file.rename(backup_file)
                logger.info(f"Moved corrupted cache to {backup_file}")
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"Failed to load embedding cache: {e}")
            logger.debug(f"Cache file path: {cache_file}")
            self._embedding_cache = {}
    
    def _save_cache(self):
        """Save embedding cache to disk."""
        cache_file = self.cache_dir / "embedding_cache.pkl"
        
        try:
            # Ensure cache directory exists
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Use atomic write to prevent corruption
            temp_file = cache_file.with_suffix('.pkl.tmp')
            
            # Use builtins.open to avoid any potential shadowing issues
            import builtins
            with builtins.open(temp_file, 'wb') as f:
                pickle.dump(self._embedding_cache, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            # Atomic rename to replace the old cache file
            temp_file.replace(cache_file)
            logger.debug(f"Successfully saved {len(self._embedding_cache)} embeddings to cache")
            
        except (OSError, IOError) as e:
            logger.warning(f"Failed to save embedding cache due to I/O error: {e}")
        except (pickle.PickleError, pickle.PicklingError) as e:
            logger.warning(f"Failed to save embedding cache due to serialization error: {e}")
        except Exception as e:
            logger.warning(f"Failed to save embedding cache: {e}")
            # Add more detailed error information
            logger.debug(f"Cache file path: {cache_file}")
            logger.debug(f"Cache directory exists: {self.cache_dir.exists()}")
            logger.debug(f"Cache size: {len(self._embedding_cache)}")
            
            # Clean up temp file if it exists
            try:
                temp_file = cache_file.with_suffix('.pkl.tmp')
                if temp_file.exists():
                    temp_file.unlink()
            except Exception:
                pass
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        import hashlib
        return hashlib.md5(f"{self.model_name}:{text}".encode()).hexdigest()
    
    def save_cache(self):
        """Manually save the embedding cache to disk."""
        self._save_cache()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        cache_file = self.cache_dir / "embedding_cache.pkl"
        cache_size_bytes = 0
        
        try:
            if cache_file.exists():
                cache_size_bytes = cache_file.stat().st_size
        except Exception:
            cache_size_bytes = 0
        
        return {
            'cache_size': len(self._embedding_cache),
            'cache_size_bytes': cache_size_bytes,
            'cache_size_mb': round(cache_size_bytes / (1024 * 1024), 2),
            'cache_dir': str(self.cache_dir),
            'cache_file_exists': cache_file.exists(),
            'model_name': self.model_name,
            'max_cache_size': self.max_cache_size,
            'cache_hit_rate': self._cache_hits / max(self._cache_requests, 1),
            'cache_hits': self._cache_hits,
            'cache_requests': self._cache_requests,
            'cache_additions': self._cache_additions
        }
    
    def _optimize_cache(self):
        """Optimize cache by removing oldest entries if cache is too large."""
        if len(self._embedding_cache) <= self.max_cache_size:
            return
        
        # Simple LRU-like approach: remove oldest entries
        # In a more sophisticated implementation, we could track access times
        cache_items = list(self._embedding_cache.items())
        entries_to_remove = len(cache_items) - self.max_cache_size
        
        for i in range(entries_to_remove):
            del self._embedding_cache[cache_items[i][0]]
        
        logger.info(f"Optimized cache: removed {entries_to_remove} entries, {len(self._embedding_cache)} remaining")
        self._save_cache()
    
    def _should_save_cache(self) -> bool:
        """Determine if cache should be saved based on additions."""
        return self._cache_additions > 0 and self._cache_additions % self.cache_save_interval == 0
    
    def validate_cache(self) -> Dict[str, Any]:
        """Validate cache integrity and fix issues."""
        validation_results = {
            'valid_entries': 0,
            'invalid_entries': 0,
            'fixed_entries': 0,
            'errors': []
        }
        
        try:
            invalid_keys = []
            
            for cache_key, embedding in self._embedding_cache.items():
                try:
                    # Validate embedding format
                    if not isinstance(embedding, list):
                        invalid_keys.append(cache_key)
                        validation_results['errors'].append(f"Invalid embedding type for key {cache_key[:20]}...")
                        continue
                    
                    # Validate embedding dimension
                    if hasattr(self, 'embedding_dim') and len(embedding) != self.embedding_dim:
                        invalid_keys.append(cache_key)
                        validation_results['errors'].append(f"Invalid embedding dimension for key {cache_key[:20]}...")
                        continue
                    
                    # Validate embedding values
                    if not all(isinstance(x, (int, float)) for x in embedding):
                        invalid_keys.append(cache_key)
                        validation_results['errors'].append(f"Invalid embedding values for key {cache_key[:20]}...")
                        continue
                    
                    validation_results['valid_entries'] += 1
                    
                except Exception as e:
                    invalid_keys.append(cache_key)
                    validation_results['errors'].append(f"Error validating key {cache_key[:20]}...: {e}")
            
            # Remove invalid entries
            for key in invalid_keys:
                del self._embedding_cache[key]
                validation_results['fixed_entries'] += 1
            
            validation_results['invalid_entries'] = len(invalid_keys)
            
            if invalid_keys:
                logger.warning(f"Removed {len(invalid_keys)} invalid cache entries")
                self._save_cache()
            
        except Exception as e:
            validation_results['errors'].append(f"Cache validation failed: {e}")
        
        return validation_results
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the embedding system."""
        try:
            import psutil
            import os
            
            # Get process info
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            return {
                'cache_hit_rate': self._cache_hits / max(self._cache_requests, 1),
                'cache_size': len(self._embedding_cache),
                'cache_size_mb': len(self._embedding_cache) * self.embedding_dim * 4 / (1024 * 1024),  # Rough estimate
                'memory_usage_mb': memory_info.rss / (1024 * 1024),
                'model_name': self.model_name,
                'embedding_dimension': getattr(self, 'embedding_dim', None),
                'batch_size': self.batch_size,
                'total_requests': self._cache_requests,
                'total_hits': self._cache_hits,
                'total_additions': self._cache_additions
            }
        except ImportError:
            # psutil not available, return basic metrics
            return {
                'cache_hit_rate': self._cache_hits / max(self._cache_requests, 1),
                'cache_size': len(self._embedding_cache),
                'model_name': self.model_name,
                'embedding_dimension': getattr(self, 'embedding_dim', None),
                'batch_size': self.batch_size,
                'total_requests': self._cache_requests,
                'total_hits': self._cache_hits,
                'total_additions': self._cache_additions
            }
        except Exception as e:
            logger.warning(f"Failed to get performance metrics: {e}")
            return {'error': str(e)}
    
    def optimize_for_performance(self):
        """Optimize the embedding system for better performance."""
        try:
            # Validate and clean cache
            validation_results = self.validate_cache()
            
            # Optimize cache size
            if len(self._embedding_cache) > self.max_cache_size:
                self._optimize_cache()
            
            # Save optimized cache
            self._save_cache()
            
            logger.info(f"Performance optimization completed: {validation_results['valid_entries']} valid entries, "
                       f"{validation_results['fixed_entries']} entries fixed")
            
            return {
                'status': 'success',
                'cache_size': len(self._embedding_cache),
                'validation_results': validation_results
            }
            
        except Exception as e:
            logger.error(f"Performance optimization failed: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a comprehensive health check of the embedding system."""
        health_status = {
            'overall_status': 'healthy',
            'checks': {},
            'warnings': [],
            'errors': []
        }
        
        try:
            # Check embedder initialization
            if self.embedder is None:
                health_status['checks']['embedder'] = 'failed'
                health_status['errors'].append('Embedder not initialized')
                health_status['overall_status'] = 'unhealthy'
            else:
                health_status['checks']['embedder'] = 'passed'
            
            # Check cache directory
            if not self.cache_dir.exists():
                health_status['checks']['cache_directory'] = 'failed'
                health_status['errors'].append(f'Cache directory does not exist: {self.cache_dir}')
                health_status['overall_status'] = 'unhealthy'
            else:
                health_status['checks']['cache_directory'] = 'passed'
            
            # Check cache file accessibility
            cache_file = self.cache_dir / "embedding_cache.pkl"
            try:
                # Test write access
                test_file = self.cache_dir / "health_check.tmp"
                import builtins
                with builtins.open(test_file, 'w') as f:
                    f.write('test')
                test_file.unlink()
                health_status['checks']['cache_write_access'] = 'passed'
            except Exception as e:
                health_status['checks']['cache_write_access'] = 'failed'
                health_status['errors'].append(f'Cannot write to cache directory: {e}')
                health_status['overall_status'] = 'unhealthy'
            
            # Check cache size
            cache_size = len(self._embedding_cache)
            if cache_size > self.max_cache_size * 1.1:  # 10% tolerance
                health_status['checks']['cache_size'] = 'warning'
                health_status['warnings'].append(f'Cache size ({cache_size}) exceeds maximum ({self.max_cache_size})')
            else:
                health_status['checks']['cache_size'] = 'passed'
            
            # Check embedding dimension consistency
            if hasattr(self, 'embedding_dim') and self._embedding_cache:
                inconsistent_embeddings = 0
                for embedding in list(self._embedding_cache.values())[:10]:  # Check first 10
                    if len(embedding) != self.embedding_dim:
                        inconsistent_embeddings += 1
                
                if inconsistent_embeddings > 0:
                    health_status['checks']['embedding_consistency'] = 'warning'
                    health_status['warnings'].append(f'{inconsistent_embeddings} embeddings have inconsistent dimensions')
                else:
                    health_status['checks']['embedding_consistency'] = 'passed'
            else:
                health_status['checks']['embedding_consistency'] = 'skipped'
            
            # Performance check
            hit_rate = self._cache_hits / max(self._cache_requests, 1)
            if hit_rate < 0.1 and self._cache_requests > 100:  # Low hit rate with significant usage
                health_status['checks']['cache_performance'] = 'warning'
                health_status['warnings'].append(f'Low cache hit rate: {hit_rate:.2%}')
            else:
                health_status['checks']['cache_performance'] = 'passed'
            
            # Set overall status based on errors
            if health_status['errors']:
                health_status['overall_status'] = 'unhealthy'
            elif health_status['warnings']:
                health_status['overall_status'] = 'degraded'
            
        except Exception as e:
            health_status['overall_status'] = 'unhealthy'
            health_status['errors'].append(f'Health check failed: {e}')
        
        return health_status
    
    async def embed_text(self, text: str, use_cache: bool = True) -> List[float]:
        """Generate embedding for a single text."""
        self._cache_requests += 1
        
        if use_cache:
            cache_key = self._get_cache_key(text)
            if cache_key in self._embedding_cache:
                self._cache_hits += 1
                return self._embedding_cache[cache_key]
        
        try:
            # Generate embedding using sentence transformers
            embedding = self.embedder.encode([text])[0].tolist()
            
            # Cache the result
            if use_cache:
                cache_key = self._get_cache_key(text)
                self._embedding_cache[cache_key] = embedding
                self._cache_additions += 1
                
                # Periodically save cache and optimize
                if self._should_save_cache():
                    self._optimize_cache()
                    self._save_cache()
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {e}")
            raise
    
    async def embed_texts(
        self, 
        texts: List[str], 
        use_cache: bool = True
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        # Check cache first if enabled
        if use_cache:
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                if cache_key in self._embedding_cache:
                    embeddings.append(self._embedding_cache[cache_key])
                else:
                    embeddings.append(None)  # Placeholder
                    uncached_texts.append(text)
                    uncached_indices.append(i)
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))
            embeddings = [None] * len(texts)
        
        # Generate embeddings for uncached texts
        if uncached_texts:
            try:
                # Use sentence transformers for batch processing
                batch_embeddings = self.embedder.encode(uncached_texts)
                
                # Process results
                for i, embedding in enumerate(batch_embeddings):
                    original_index = uncached_indices[i]
                    embedding_list = embedding.tolist()
                    
                    embeddings[original_index] = embedding_list
                    
                    # Cache the result
                    if use_cache:
                        cache_key = self._get_cache_key(uncached_texts[i])
                        self._embedding_cache[cache_key] = embedding_list
                        self._cache_additions += 1
                
                # Save cache after batch processing and optimize if needed
                if use_cache and uncached_texts:
                    if len(self._embedding_cache) > self.max_cache_size:
                        self._optimize_cache()
                    self._save_cache()
                
            except Exception as e:
                logger.error(f"Failed to generate batch embeddings: {e}")
                raise
        
        return embeddings
    
    async def embed_components(
        self,
        components: List[Dict[str, Any]],
        text_field: str = 'content'
    ) -> List[Dict[str, Any]]:
        """Generate embeddings for document components.

        Automatically uses ``enriched_content`` when present on a component so
        that contextual embedding text (document title + summaries + chunk text)
        is always embedded instead of raw chunk text.
        """
        try:
            # Prefer enriched_content for embedding when available — this is the
            # contextual embedding string built by DocumentChunker.build_enriched_text.
            texts = [comp.get('enriched_content') or comp.get(text_field, '') for comp in components]
            
            # Generate embeddings
            embeddings = await self.embed_texts(texts)
            
            # Add embeddings to components
            enhanced_components = []
            for i, component in enumerate(components):
                enhanced_component = component.copy()
                enhanced_component['embedding'] = embeddings[i]
                enhanced_component['embedding_model'] = self.model_name
                enhanced_component['embedded_at'] = datetime.now(timezone.utc).isoformat()
                enhanced_components.append(enhanced_component)
            
            return enhanced_components
            
        except Exception as e:
            logger.error(f"Failed to embed components: {e}")
            raise
    
    def calculate_similarity(
        self, 
        embedding1: List[float], 
        embedding2: List[float],
        method: str = 'cosine'
    ) -> float:
        """Calculate similarity between two embeddings."""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            if method == 'cosine':
                # Cosine similarity
                dot_product = np.dot(vec1, vec2)
                norm1 = np.linalg.norm(vec1)
                norm2 = np.linalg.norm(vec2)
                
                if norm1 == 0 or norm2 == 0:
                    return 0.0
                
                return dot_product / (norm1 * norm2)
            
            elif method == 'euclidean':
                # Euclidean distance (converted to similarity)
                distance = np.linalg.norm(vec1 - vec2)
                return 1.0 / (1.0 + distance)
            
            elif method == 'dot_product':
                # Dot product similarity
                return np.dot(vec1, vec2)
            
            else:
                raise ValueError(f"Unknown similarity method: {method}")
                
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0
    
    def find_similar_embeddings(
        self, 
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int = 10,
        threshold: float = 0.7,
        method: str = 'cosine'
    ) -> List[Tuple[int, float]]:
        """Find most similar embeddings to a query embedding."""
        try:
            similarities = []
            
            for i, candidate in enumerate(candidate_embeddings):
                similarity = self.calculate_similarity(
                    query_embedding, 
                    candidate, 
                    method=method
                )
                
                if similarity >= threshold:
                    similarities.append((i, similarity))
            
            # Sort by similarity (descending) and return top_k
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Failed to find similar embeddings: {e}")
            return []
    
    def get_embedding_statistics(self) -> Dict[str, Any]:
        """Get statistics about embeddings."""
        try:
            cache_size = len(self._embedding_cache)
            
            # Calculate cache size in MB
            cache_file = self.cache_dir / "embedding_cache.pkl"
            cache_size_mb = 0
            if cache_file.exists():
                cache_size_mb = cache_file.stat().st_size / (1024 * 1024)
            
            return {
                'model_name': self.model_name,
                'cached_embeddings': cache_size,
                'cache_size_mb': round(cache_size_mb, 2),
                'cache_directory': str(self.cache_dir),
                'batch_size': self.batch_size,
                'max_workers': self.max_workers
            }
            
        except Exception as e:
            logger.error(f"Failed to get embedding statistics: {e}")
            return {'error': str(e)}
    
    def clear_cache(self):
        """Clear the embedding cache."""
        try:
            self._embedding_cache.clear()
            
            # Remove cache file
            cache_file = self.cache_dir / "embedding_cache.pkl"
            if cache_file.exists():
                cache_file.unlink()
            
            logger.info("Embedding cache cleared")
            
        except Exception as e:
            logger.error(f"Failed to clear embedding cache: {e}")
    
    def export_embeddings(
        self, 
        output_path: str,
        format: str = 'json'
    ) -> Dict[str, Any]:
        """Export embeddings to file."""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            if format == 'json':
                # Convert to JSON-serializable format
                export_data = {
                    'model_name': self.model_name,
                    'exported_at': datetime.now(timezone.utc).isoformat(),
                    'embedding_dimension': getattr(self, 'embedding_dim', None),
                    'total_embeddings': len(self._embedding_cache),
                    'embeddings': {}
                }
                
                for cache_key, embedding in self._embedding_cache.items():
                    export_data['embeddings'][cache_key] = {
                        'embedding': embedding,
                        'dimension': len(embedding)
                    }
                
                # Use builtins.open for consistency
                import builtins
                with builtins.open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            elif format == 'numpy':
                # Export as numpy arrays
                embeddings_array = np.array(list(self._embedding_cache.values()))
                keys_array = np.array(list(self._embedding_cache.keys()))
                
                np.savez(
                    output_file,
                    embeddings=embeddings_array,
                    keys=keys_array,
                    model_name=self.model_name
                )
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            return {
                'status': 'success',
                'exported_embeddings': len(self._embedding_cache),
                'output_path': str(output_file),
                'format': format
            }
            
        except Exception as e:
            logger.error(f"Failed to export embeddings: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            import sys
            if hasattr(sys, 'meta_path') and sys.meta_path is not None:
                if hasattr(self, '_embedding_cache'):
                    self._save_cache()
        except Exception:
            pass