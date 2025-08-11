## FEATURE:

- The goal of this feature is to correct the inmplentation of AI Tools in this application using Langchain tools and agents. 
- Unified Tool Discovery - Single interface for all tools
- Tool Categories - Group tools by domain (banking, documents, analysis)
- Dynamic Tool Loading - Runtime tool registration based on available data- Dynamic Tool Loading - Runtime tool registration based on available data
- Provide testing that simulates user conversations that would trigger the use of the tools.

## EXAMPLES:

In the `examples/` folder, there is a README for you to read to understand what the example is all about and also how to structure your own README when you create documentation for the above feature.


Don't copy any of these examples directly, it is for a different project entirely. But use this as inspiration and for best practices.

## DOCUMENTATION:

Lanchain Tools Documentation: https://python.langchain.com/docs/concepts/tools/
Lanchain Tool Calling Documentation: https://python.langchain.com/docs/concepts/tool_calling/
Lanchain Agents:https://python.langchain.com/docs/concepts/agents/

## OTHER CONSIDERATIONS:

- The solution should implement the Langchain framework and implement patterns for Tooling and Agents
- The example use case for the existing tooling is getting bank financials from an API in the tool inventory when asked about 10K/10Q based finacials for a question or calculation.
- Refactor the BankingTools and Call Report Tools as necessary to make compliant with the new solution. 
- Model parameters (temperature, max tokens, etc.)