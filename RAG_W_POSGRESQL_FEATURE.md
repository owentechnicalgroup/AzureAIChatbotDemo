## FEATURE:

The goal of this feature is to add RAG capabilities to the chatbot application. 

- Add a new user interface for the exiting chat application using Streamlit
- Add a RAG component to the chat application using ChromaDB
- Create a user interface and application that allows the user to upload documents into the RAG
- The upload should create vector embeddings that are stored in the ChromaDB
- Implement the Chain of Thought feature included in the documentation.
- Incorporate changes into the existing application 

## EXAMPLES:

In the `examples/` folder, there is a README for you to read to understand what the example is all about and also how to structure your own README when you create documentation for the above feature.

- `examples/container-app-openai` - This example has example Python code that shows an implementation of a RAG and user interface using ChromaDB and Streamlit


## DOCUMENTATION:

Article outlining a similar approache: https://learn.microsoft.com/en-us/samples/azure-samples/container-apps-openai/container-apps-openai/
ChromaDB documentation: https://docs.trychroma.com/docs/overview/introduction
Langchain documenation on ChromaDB: https://python.langchain.com/docs/integrations/vectorstores/chroma/
Streamlit documentation: https://docs.streamlit.io/


## OTHER CONSIDERATIONS:
- Split documents into manageable chunks (e.g., 500–1000 tokens) to improve retrieval granularity.
- Store metadata (e.g., source, title, tags) alongside embeddings to support filtering and context-aware retrieval.
- Use ChromaDB in perstenmode.
- Use Chroma as a retriever in LangChain with VectorStoreRetriever
- Combine retrieval with prompt templates and Azure OpenAI completions to form a coherent response pipeline
- Use LangChain’s memory components to maintain conversational context and persist in Azure Application Insights
- Use Azure Container Apps to deploy Chroma
