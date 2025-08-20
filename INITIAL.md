## FEATURE:

- A Python-based command-line chatbot application that leverages Azure OpenAI GPT-4 through Azure AI Foundry and LangChain integration. This foundational implementation will serve as a stepping stone for future web interface and advanced AI capabilities.
- Conversational Interface: Command-line interface with interactive chat session, Support for configurable system prompts via environment variables or command-line arguments, Persistent conversation history within each chat session, Graceful session termination with conversation summary option
- Azure Integration: Azure OpenAI Service integration using GPT-4 model, LangChain framework for conversation management and prompt templating,Azure AI Studio agent configuration support,Connection pooling and request retry logic for reliability
- Logging & Monitoring: Structured JSON logging using Python's structlog library (compatible with Azure Application Insights ingestion),Local log files with rotation (daily/size-based), Log levels: DEBUG, INFO, WARNING, ERROR, Captured metrics: response times, token usage, error rates, conversation length
- Error Handling: Verbose error descriptions for Azure service connectivity issues, Graceful degradation when services are temporarily unavailable, Input validation and sanitization, Rate limiting awareness with user-friendly messaging
- Successful connection to Azure OpenAI GPT-4
- Multi-turn conversation with memory
- Structured JSON logging to local files
- Configurable system prompts
- Comprehensive error handling and user feedback
- Clean conversation history management
- Documentation for setup and usage

## EXAMPLES:

In the `examples/` folder, there is a README for you to read to understand what the example is all about and also how to structure your own README when you create documentation for the above feature.

- `examples/aopenai` - This repository provides practical resources and code samples for building solutions with Azure OpenAI Service, Azure AI Foundry, and advanced agent-based architectures
- `examples/azure_openai_langchain_sample` - This repository contains various examples of how to use LangChain, a way to use natural language to interact with LLM, a large language model from Azure OpenAI Service
- `examples/sample-app-aoai-chatGPT` - Sample code for a simple web chat experience through Azure OpenAI, including Azure OpenAI On Your Data
  Don't copy any of these examples directly, it is for a different project entirely. But use this as inspiration and for best practices.

## DOCUMENTATION:

Main Azure OpenAI Documentation: https://learn.microsoft.com/en-us/azure/ai-services/openai/
Azure OpenAI Python Quickstart: https://learn.microsoft.com/en-us/azure/ai-services/openai/quickstart
API Reference (Latest 2024-05-01-preview): https://learn.microsoft.com/en-us/azure/ai-foundry/openai/references/on-your-data
LangChain with Azure AI Foundry: https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/langchain
Azure AI for Python Developers: https://learn.microsoft.com/en-us/azure/developer/python/azure-ai-for-python-developers
LangChain Azure OpenAI: https://python.langchain.com/docs/integrations/llms/azure_openai/

## OTHER CONSIDERATIONS:

- Logging structure compatible with Azure Application Insights
- Modular architecture supporting web interface integration
- Configuration system ready for additional Azure services
- Extensible prompt management for future RAG Implementation
- Environment variables for Azure credentials and endpoints
- Configurable system prompts
- Logging level configuration
- Model parameters (temperature, max tokens, etc.)
