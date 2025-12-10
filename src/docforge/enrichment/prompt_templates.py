"""Prompt templates for context enrichment."""

# Anthropic's Contextual Retrieval prompt
CONTEXT_ENRICHMENT_PROMPT = """<document>
{whole_document}
</document>

Here is the chunk we want to situate within the whole document:
<chunk>
{chunk_content}
</chunk>

Please give a short, succinct context (1-2 sentences) to situate this chunk within the overall document for improved retrieval. 
Answer only with the context, nothing else."""


# Alternative shorter prompt for cost optimization
SHORT_CONTEXT_PROMPT = """Document: {whole_document}

Chunk: {chunk_content}

Provide 1-2 sentences of context to situate this chunk within the document:"""


# Structured document prompt (for documents with clear sections)
STRUCTURED_CONTEXT_PROMPT = """<document_metadata>
Title: {doc_title}
Type: {doc_type}
Date: {doc_date}
</document_metadata>

<document>
{whole_document}
</document>

<chunk>
{chunk_content}
</chunk>

Provide a brief context (1-2 sentences) that identifies where this chunk fits in the document structure and what it discusses:"""


def get_prompt_template(style: str = "default") -> str:
    """Get prompt template by style name.
    
    Args:
        style: Template style - 'default', 'short', or 'structured'
        
    Returns:
        Prompt template string
    """
    templates = {
        "default": CONTEXT_ENRICHMENT_PROMPT,
        "short": SHORT_CONTEXT_PROMPT,
        "structured": STRUCTURED_CONTEXT_PROMPT,
    }
    return templates.get(style, CONTEXT_ENRICHMENT_PROMPT)
