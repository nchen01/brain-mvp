"""Context enricher for adding document-level context to chunks.

Implements Anthropic's Contextual Retrieval method to improve RAG accuracy
by prepending situational context to each chunk.
"""

import logging
from typing import Optional, Dict, Any
from openai import OpenAI, OpenAIError
from .prompt_templates import get_prompt_template

logger = logging.getLogger(__name__)


class ContextEnricher:
    """Enriches chunks with document-level context using LLM."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        prompt_style: str = "default",
        max_context_words: int = 100,
        temperature: float = 0.3,
        enabled: bool = True
    ):
        """Initialize context enricher.
        
        Args:
            api_key: OpenAI API key (if None, enrichment will be skipped)
            model: OpenAI model to use for context generation
            prompt_style: Template style ('default', 'short', 'structured')
            max_context_words: Maximum words in generated context
            temperature: LLM temperature (lower = more deterministic)
            enabled: Whether enrichment is enabled
        """
        self.api_key = api_key
        self.model = model
        self.prompt_style = prompt_style
        self.max_context_words = max_context_words
        self.temperature = temperature
        self.enabled = enabled and api_key is not None
        
        # Initialize OpenAI client if API key provided
        self.client = None
        if self.api_key:
            try:
                self.client = OpenAI(api_key=api_key)
                logger.info(f"Context enricher initialized with model: {model}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.enabled = False
        else:
            logger.warning("No OpenAI API key provided - context enrichment disabled")
            self.enabled = False
    
    def enrich_chunk(
        self,
        whole_document: str,
        chunk_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate contextual enrichment for a chunk.
        
        Args:
            whole_document: Full document text for context
            chunk_content: The specific chunk to enrich
            metadata: Optional metadata for structured prompts
            
        Returns:
            Enriched chunk text with context prepended, or original chunk if enrichment fails/disabled
        """
        # Return original chunk if enrichment is disabled
        if not self.enabled:
            logger.debug("Context enrichment disabled - returning original chunk")
            return chunk_content
        
        # Return original chunk if inputs are invalid
        if not whole_document or not chunk_content:
            logger.warning("Invalid inputs for context enrichment")
            return chunk_content
        
        try:
            # Build prompt from template
            prompt = self._build_prompt(whole_document, chunk_content, metadata)
            
            # Call LLM to generate context
            context = self._generate_context(prompt)
            
            if context:
                # Prepend context to chunk
                enriched = f"{context}\n\n{chunk_content}"
                logger.debug(f"Successfully enriched chunk (context: {len(context)} chars)")
                return enriched
            else:
                logger.warning("No context generated - returning original chunk")
                return chunk_content
                
        except Exception as e:
            logger.error(f"Error enriching chunk: {e}")
            # Gracefully fallback to original chunk
            return chunk_content
    
    def _build_prompt(
        self,
        whole_document: str,
        chunk_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt from template.
        
        Args:
            whole_document: Full document text
            chunk_content: Chunk to enrich
            metadata: Optional metadata
            
        Returns:
            Formatted prompt string
        """
        template = get_prompt_template(self.prompt_style)
        
        # For structured prompts, use metadata if available
        if self.prompt_style == "structured" and metadata:
            return template.format(
                whole_document=whole_document[:10000],  # Limit doc length
                chunk_content=chunk_content,
                doc_title=metadata.get('title', 'Unknown'),
                doc_type=metadata.get('type', 'Document'),
                doc_date=metadata.get('date', 'Unknown')
            )
        else:
            # Standard prompt
            return template.format(
                whole_document=whole_document[:10000],  # Limit to 10K chars
                chunk_content=chunk_content
            )
    
    def _generate_context(self, prompt: str) -> Optional[str]:
        """Generate context using LLM.
        
        Args:
            prompt: Formatted prompt
            
        Returns:
            Generated context text or None if failed
        """
        if not self.client:
            return None
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that provides brief, accurate context for document chunks."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=150,  # Limit context length
            )
            
            context = response.choices[0].message.content.strip()
            
            # Validate context length
            word_count = len(context.split())
            if word_count > self.max_context_words:
                logger.warning(f"Context too long ({word_count} words), truncating to {self.max_context_words}")
                words = context.split()[:self.max_context_words]
                context = ' '.join(words) + '...'
            
            return context
            
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating context: {e}")
            return None
    
    def enrich_chunks_batch(
        self,
        whole_document: str,
        chunks: list,
        metadata: Optional[Dict[str, Any]] = None
    ) -> list:
        """Enrich multiple chunks in batch.
        
        Args:
            whole_document: Full document text
            chunks: List of chunk texts to enrich
            metadata: Optional metadata
            
        Returns:
            List of enriched chunk texts
        """
        enriched_chunks = []
        
        for i, chunk in enumerate(chunks):
            logger.debug(f"Enriching chunk {i+1}/{len(chunks)}")
            enriched = self.enrich_chunk(whole_document, chunk, metadata)
            enriched_chunks.append(enriched)
        
        return enriched_chunks
    
    @property
    def is_enabled(self) -> bool:
        """Check if enrichment is enabled."""
        return self.enabled
    
    def get_stats(self) -> Dict[str, Any]:
        """Get enricher statistics and configuration.
        
        Returns:
            Dictionary with enricher stats
        """
        return {
            'enabled': self.enabled,
            'model': self.model,
            'prompt_style': self.prompt_style,
            'max_context_words': self.max_context_words,
            'temperature': self.temperature,
            'has_api_key': self.api_key is not None
        }
