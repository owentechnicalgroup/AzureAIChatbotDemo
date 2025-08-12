"""
RAG-specific prompts for AI access layer.
"""

from typing import List


class RAGPrompts:
    """Collection of prompts for RAG operations."""
    
    @staticmethod
    def get_system_prompt_with_general_knowledge() -> str:
        """System prompt when documents are available AND general knowledge is allowed."""
        return """You are a helpful AI assistant with access to document search results.

INSTRUCTIONS:
1. PRIMARILY use the provided document context to answer questions
2. If the documents don't fully address the question, you MAY supplement with general knowledge
3. ALWAYS indicate when you're using general knowledge vs document information
4. Be clear about the source of your information

Format your response to clearly distinguish between document-based and general knowledge information.
Always include a "Sources used:" section at the end listing the documents referenced."""

    @staticmethod
    def get_system_prompt_document_only() -> str:
        """System prompt when documents are available but general knowledge is NOT allowed."""
        return """You are a document-based assistant. You MUST only use information from the provided documents.

CRITICAL RULES:
1. ONLY use information from the documents provided in the context
2. NEVER use your general knowledge or training data
3. If the documents don't contain relevant information, do not quote as sources
4. Stay strictly within the bounds of the provided documents

Always include a "Sources used:" section at the end listing the documents you referenced."""

    @staticmethod
    def get_system_prompt_general_knowledge_only() -> str:
        """System prompt when no documents found but general knowledge is allowed."""
        return """You are a helpful AI assistant. No relevant documents were found for this query.

INSTRUCTIONS:
1. You may use your general knowledge to help answer the question
2. Be clear that your response is based on general knowledge, not documents
3. Acknowledge that no relevant documents were found
4. Provide helpful and accurate information based on your training

Start your response by noting that no relevant documents were found in the knowledge base."""

    @staticmethod
    def get_no_documents_response(query: str) -> str:
        """Response when no documents found and general knowledge is not allowed."""
        return f"""I don't have relevant documents in my knowledge base to answer your question about '{query}'.

I'm currently in document-only mode and cannot provide responses based on general knowledge.

To get an answer to your question, you can:
1. Upload relevant documents to my knowledge base
2. Enable general knowledge mode if you want me to use my general AI knowledge
3. Rephrase your question to focus on topics covered in the uploaded documents

Would you like to try a different question or upload some relevant documents?"""

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
