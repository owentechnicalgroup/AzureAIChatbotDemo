"""
RAG-specific prompts for AI access layer.
"""

from typing import List, Dict, Any


class RAGPrompts:
    """Collection of prompts for RAG operations."""
    
    @staticmethod
    def get_system_prompt(use_general_knowledge: bool = False) -> str:
        """Get system prompt for RAG responses."""
        base_prompt = """You are a helpful AI assistant that answers questions based on provided document context.

INSTRUCTIONS:
1. Use the provided document context to answer questions accurately
2. Always cite your sources when using document information
3. Be specific and detailed in your responses
4. If the document context doesn't contain enough information, acknowledge this clearly"""

        if use_general_knowledge:
            base_prompt += """
5. If document context is insufficient, you may supplement with general knowledge
6. Clearly distinguish between document-based and general knowledge information"""
        else:
            base_prompt += """
5. Only use the provided document context - do not add information from general knowledge
6. If you cannot answer based on the documents, say so clearly"""

        return base_prompt

    @staticmethod
    def format_context_prompt(sources: List[Dict[str, Any]], query: str) -> str:
        """Format document context for RAG prompt."""
        if not sources:
            return f"Query: {query}\n\nNo relevant documents found."
        
        context_parts = [f"Query: {query}", "", "Document Context:"]
        
        for i, source in enumerate(sources, 1):
            content = source.get('content', '')
            source_name = source.get('source', 'Unknown')
            score = source.get('score', 0.0)
            
            context_parts.extend([
                f"[Source {i}] {source_name} (relevance: {score:.2f})",
                content,
                ""
            ])
        
        return "\n".join(context_parts)

    @staticmethod
    def get_no_context_prompt(query: str, use_general_knowledge: bool = False) -> str:
        """Get prompt when no document context is available."""
        if use_general_knowledge:
            return f"""Query: {query}

No relevant documents found in the knowledge base. You may answer using your general knowledge, but please note that your response is not based on uploaded documents."""
        else:
            return f"""Query: {query}

I don't have relevant information in my document knowledge base to answer this question. Please upload relevant documents or ask a question about the documents that are available."""

    @staticmethod
    def get_search_refinement_prompt(original_query: str, results_count: int) -> str:
        """Get prompt for search refinement suggestions."""
        if results_count == 0:
            return f"""No documents found for: "{original_query}"

Try:
- Using different keywords or phrases
- Being more specific or more general
- Checking if relevant documents are uploaded"""
        else:
            return f"Found {results_count} relevant document(s) for: \"{original_query}\""