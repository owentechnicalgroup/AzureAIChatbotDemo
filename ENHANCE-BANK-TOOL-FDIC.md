## FEATURE:

- The goal of this feature is to enhance the existing bank_lookup_tool to use the BankFind Suite API made available by the FDIC
- The bank analysis tool should be updated to use this API as well
- The existing functionality to lookup the RSSID and bank information should be enhanced to use the data available from /institution node of the BankFind Suite API API
- Update to the BankLookup and BankAnalysisInput to reflect the fields available through the /institution node
- The solution should continue to leverage LangChain framework and should follow the pattern establish in this application for AI use of tools.
- Do not incorporate the other APIs available like Location, History, Summary, Failure, SOD, Financial or Demographics Data. We will incorporate those in a future initative.
- Be sure to correct the bank_lookup_tool with the additional prompt instructions to include enhancements created during this enhancement.
- The AI Agent should be able to search for institution by name, city and county
- The API should be stored in a secure manner. Here is the API Key gMeWeAXp4GeNVRB9cN9b3gNV001gqrt3qbhV7KGu

## Examples:

- See application source for example tool implementation /tools/atomic/bank_lookup_tool.py
- /tools/composit/bank_analysis_tool.py
- /tools/dynamic.loader.py

## Documentation

- FDIC Website for BankFindSuite API https://api.fdic.gov/banks/docs/#/
- Full API documentation https://api.fdic.gov/banks/docs/swagger.yaml
