## FEATURE: AGENT_CALL_REPORT_TOOLING

- **Call Report Data Integration for AI Agent Financial Analysis** - A comprehensive tooling system that provides AI agents with access to FFIEC Call Report data through a mock service API, enabling automated calculation of financial ratios like Return on Assets (ROA) and other metrics based on banking policy documents stored in the RAG system.

- **Mock Call Report API Service**: RESTful API service that simulates access to current quarter FFIEC Call Report data, Legal Entity Identifier lookup service for bank name resolution, Support for standard Call Report schedules (RC - Balance Sheet, RI - Income Statement, etc.), JSON response format with field names, values, and metadata, Error handling for missing banks, unavailable data, and service outages

- **AI Agent Tool Integration**: LangChain tool wrapper for Call Report API integration, Cross-reference capabilities with existing RAG document information, Intelligent field lookup based on schedule identifiers and field names/IDs, Automatic data validation and availability checking before ratio calculations, Policy-driven ratio calculation support using RAG-stored banking procedures

- **Financial Ratio Calculation Framework**: ROA calculation using Net Income (Schedule RI) and Total Assets (Schedule RC), Extensible framework for additional ratios based on RAG policy documents, Data validation ensuring required fields are available before calculations, Clear error messaging when data is insufficient or API is unavailable, Integration with existing Azure OpenAI agent for contextual ratio analysis

- **RAG System Integration**: Cross-reference Call Report data with policy documents like "Mo's Bank Credit Procedure.docx", Context-aware ratio selection based on document analysis, Automated field mapping from policy requirements to Call Report schedules, Enhanced AI responses combining quantitative data with qualitative policy guidance

- **Error Handling & User Communication**: Bank not found scenarios with clear user messaging, Missing data field identification and user notification, API availability checking with graceful degradation, Detailed logging of data retrieval attempts and failures, User-friendly explanations when calculations cannot be performed

## EXAMPLES:

In the `src/tools/` folder structure:
- `src/tools/call_report/` - Call Report API integration and tools
- `src/tools/call_report/api_client.py` - Mock Call Report API service implementation  
- `src/tools/call_report/langchain_tools.py` - LangChain tool wrappers for AI agent integration
- `src/tools/call_report/financial_calculators.py` - Financial ratio calculation functions
- `src/tools/call_report/data_models.py` - Pydantic models for Call Report data structures

Don't copy existing implementations directly, but use the project's established patterns for:
- Azure OpenAI integration via LangChain
- Structured logging with appropriate log_type categorization
- Pydantic data validation and settings management
- Error handling patterns with rich user feedback

## DOCUMENTATION:

FFIEC Call Report Documentation: https://www.ffiec.gov/call_reports.htm
Call Report Schedules Reference: https://www.ffiec.gov/pdf/FFIEC_forms/FFIEC031_041_202403_f.pdf
LangChain Tools Documentation: https://python.langchain.com/docs/modules/agents/tools/
Azure OpenAI Function Calling: https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/function-calling
Financial Ratio Analysis: https://www.fdic.gov/regulations/safety/manual/section3-1.pdf
Banking Supervision Manual: https://www.federalreserve.gov/publications/supervision_bhc.htm

## OTHER CONSIDERATIONS:

- **Mock Data Generation**: Create realistic Call Report data samples for testing and demonstration
- **Schedule Mapping**: Implement comprehensive mapping between FFIEC schedule identifiers and field names
- **RAG Integration**: Ensure seamless integration with existing document processing and retrieval systems
- **Tool Registration**: Register Call Report tools with the AI agent's tool registry for automatic discovery
- **Performance**: Cache frequently accessed bank data to reduce API calls during ratio calculations
- **Compliance**: Follow banking data handling best practices even in mock implementation
- **Extensibility**: Design API to easily support additional Call Report schedules and derived calculations
- **Logging Integration**: Use project's standardized log_type categories (SYSTEM, PERFORMANCE, AZURE_OPENAI)
- **Configuration**: Add Call Report API settings to existing configuration management system
- **Testing**: Create comprehensive test suite including mock API responses and ratio calculation edge cases
- **Documentation**: Update project README and create tool usage examples for developers