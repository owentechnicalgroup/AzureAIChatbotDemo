"""
RAG-specific prompts for AI access layer.
"""

from typing import List


class RAGPrompts:
    """Simplified RAG prompts - now only handles document context formatting.
    
    Note: System prompts for RAG behavior are now handled by the ChatbotAgent's 
    enhanced system prompt. This class only provides document context formatting.
    """
    
    @staticmethod
    def build_context_prompt(search_results: List) -> str:
        """Build context prompt from search results."""
        if not search_results:
            return "No relevant documents found."
        
        # Group chunks by document for document-level citations
        documents = {}
        for result in search_results:
            source = result.source if hasattr(result, 'source') else result.get('source', 'Unknown')
            content = result.content if hasattr(result, 'content') else result.get('content', '')
            
            if source not in documents:
                documents[source] = []
            documents[source].append(content)
        
        # Build context with document-level grouping
        context_parts = ["Document Context:"]
        
        for doc_name, chunks in documents.items():
            context_parts.append(f"\n=== {doc_name} ===")
            for chunk in chunks:
                context_parts.append(chunk)
                context_parts.append("")
                      
        return "\n".join(context_parts)
