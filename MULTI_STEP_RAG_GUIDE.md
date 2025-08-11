# Multi-Step RAG Integration Usage Guide

## Overview

The ChatbotAgent now supports both simple conversation mode and multi-step RAG-enabled conversations through LangChain agent integration.

## Key Features

✅ **Dual Processing Modes:**

- **Simple Mode**: Direct conversation chain (faster, for general queries)
- **Multi-Step Mode**: Agent executor with RAG tools (intelligent document search)

✅ **Intelligent Tool Usage:**

- Agent automatically decides when to use RAG tools based on user queries
- Optimized for Azure OpenAI with proper async/await patterns
- Built-in conversation memory for context preservation

✅ **Azure-Optimized:**

- Uses Azure OpenAI embeddings and chat completion
- Proper error handling and logging
- Performance monitoring and observability

## Usage Examples

### 1. Simple Mode Chatbot (No RAG)

```python
from src.config.settings import get_settings
from src.chatbot.agent import ChatbotAgent

# Get settings
settings = get_settings()

# Create simple chatbot
chatbot = ChatbotAgent(
    settings=settings,
    enable_multi_step=False  # Simple mode
)

# Process message
response = chatbot.process_message("What is the capital of France?")
print(response['content'])
print(f"Processing mode: {response['processing_mode']}")  # Output: simple
```

### 2. Multi-Step RAG-Enabled Chatbot

```python
from src.config.settings import get_settings
from src.chatbot.agent import ChatbotAgent
from src.rag.rag_tool import RAGSearchTool
from src.rag.retriever import RAGRetriever

# Get settings
settings = get_settings()

# Create RAG components
retriever = RAGRetriever(settings=settings)
rag_tool = RAGSearchTool(rag_retriever=retriever)

# Create multi-step chatbot
chatbot = ChatbotAgent(
    settings=settings,
    tools=[rag_tool],
    enable_multi_step=True
)

# Simple conversation (won't use RAG tool)
response1 = chatbot.process_message("Hello, how are you?")
print(f"Mode: {response1['processing_mode']}")  # multi-step (but no tool used)

# RAG-enabled query (will use document search)
response2 = chatbot.process_message("What information is available in the documents?")
print(f"Mode: {response2['processing_mode']}")  # multi-step (with tool usage)
print(response2['content'])
```

### 3. Streaming Responses

```python
# Both modes support streaming
for chunk in chatbot.stream_response("Tell me about the company policies"):
    if chunk.get('is_streaming'):
        print(chunk['content'], end='', flush=True)
    elif chunk.get('is_final'):
        print("\n[Stream complete]")
```

## Architecture Overview

### Simple Mode Flow

```
User Query → ChatbotAgent → Conversation Chain → Azure OpenAI → Response
```

### Multi-Step Mode Flow

```
User Query → ChatbotAgent → Agent Executor → Decision: Use RAG Tool?
                                           ├─ Yes → RAG Search → Context → Azure OpenAI → Response
                                           └─ No → Direct → Azure OpenAI → Response
```

## RAG Tool Integration Details

### RAGSearchTool Features

- **LangChain BaseTool**: Full compatibility with LangChain agents
- **Structured Input**: Pydantic schema for query validation
- **Async Support**: Optimized for Azure OpenAI async operations
- **Source Attribution**: Includes document sources in responses
- **Configurable**: Adjustable chunk size, score threshold, max results

### When RAG Tool is Used

The agent intelligently decides to use the RAG tool when:

- User asks about documents, policies, or procedures
- User references information from uploaded files
- Query contains phrases like "what does the document say"
- User asks for specific factual information from knowledge base

### When Simple Chain is Used

For general conversations:

- Greetings and casual conversation
- General knowledge questions
- Creative tasks (writing, brainstorming)
- Questions that don't require document search

## Configuration Options

### ChatbotAgent Parameters

- `settings`: Application settings (required)
- `conversation_id`: Unique conversation identifier (optional)
- `system_prompt`: Custom system prompt (optional)
- `tools`: List of LangChain tools (optional)
- `enable_multi_step`: Enable agent executor mode (default: False)

### Response Format

```python
{
    'content': 'The response text...',
    'conversation_id': 'uuid-string',
    'message_count': 1,
    'response_time': 1.23,
    'processing_mode': 'multi-step|simple',
    'timestamp': '2024-01-01T12:00:00Z'
}
```

## Performance Considerations

### Multi-Step vs Simple Mode

- **Simple Mode**: ~0.5-2s response time, lower token usage
- **Multi-Step Mode**: ~1-5s response time (includes tool evaluation), higher token usage for complex queries

### Best Practices

1. **Use Simple Mode** for general chatbots without document search needs
2. **Use Multi-Step Mode** when users need access to uploaded documents
3. **Monitor Response Times** via the included logging and performance metrics
4. **Optimize RAG Tool** by adjusting chunk_size and score_threshold parameters

## Logging and Observability

The implementation includes comprehensive logging:

```
- Tool usage decisions and performance
- Processing mode selection (simple vs multi-step)
- Azure OpenAI API calls and response times
- Memory management and conversation context
- Error handling with structured error reporting
```

All logs are structured and include:

- `component`: chatbot_agent, rag_search_tool, etc.
- `conversation_id`: For tracking conversations
- `processing_mode`: simple or multi-step
- `tool_count`: Number of available tools
- `response_time`: Processing duration

## Testing

Run the integration test to verify functionality:

```bash
python test_rag_chatbot.py
```

This validates:

- ✅ Multi-step chatbot creation with RAG tools
- ✅ Simple mode chatbot creation
- ✅ Message processing in both modes
- ✅ Performance metrics collection
- ✅ Azure OpenAI integration

## Next Steps

1. **Add More Tools**: Extend with additional LangChain tools (web search, calculators, etc.)
2. **Document Upload**: Implement document upload interface for RAG content
3. **Advanced Memory**: Add conversation summarization for long-term memory
4. **UI Integration**: Connect to Streamlit or web interface

The implementation provides a solid foundation for both simple and advanced conversational AI applications with Azure OpenAI.
