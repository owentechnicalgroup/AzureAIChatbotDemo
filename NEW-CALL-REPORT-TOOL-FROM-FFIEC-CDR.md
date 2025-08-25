## FEATURE:

- The goal of this feature is add a new atomic tool ffiec_call_report_data_tool to pull call report information from the FFIEC CDR Public Data Distribution.
- This should be included as a new atomic tool and should follow the pattern of implementing the langchain.tools libraries as is found in this /tools folder of this application.
- The Tool should be incorporated into the bank_analysis tool to allow that analysis to include call information from fifeac.  
- The tool will use the discovery services to determine the latest call report avaiable for the Bank given the bank RSSID
- And call the data retreival RetrieveFacsimile to pull the call report Data
- Cache the results so that the call report data is available to the agent in the current session.
- The API should be stored in a secure manner. Here is the API Key eWzacyA4rYGaQEYqBnQO

## Examples:
pythondef get_latest_filing(rssd_id):
    # Define recent quarters to check (most recent first)
    recent_periods = [
        "2024-06-30",  # Q2 2024
        "2024-03-31",  # Q1 2024
        "2023-12-31",  # Q4 2023
        "2023-09-30",  # Q3 2023
    ]
    
    for period in recent_periods:
        try:
            filing = api.RetrieveFacsimile(
                rssd_id=rssd_id,
                reporting_period=period
            )
            if filing:  # If data exists for this period
                return filing, period
        except:
            continue  # Try next period
    
    return None, None
	
pythondef get_latest_filing_smart(rssd_id):
    # Get all available reporting periods
    periods = api.RetrieveReportingPeriods()
    
    # Sort periods newest to oldest
    sorted_periods = sorted(periods, reverse=True)
    
    # Check if this bank filed for recent periods
    for period in sorted_periods[:4]:  # Check last 4 periods
        filers = api.RetrieveFilersSinceDate(
            reporting_period=period,
            since_date=period  # Gets all filers for that period
        )
        
        if rssd_id in filers:
            return api.RetrieveFacsimile(rssd_id, period), period
    
    return None, None
	
## Documentation
- FFIEC Description: https://cdr.ffiec.gov/public/PWS/PWSPage.aspx
- Retreival Service: https://cdr.ffiec.gov/public/pws/webservices/retrievalservice.asmx
- Service Decription: https://cdr.ffiec.gov/public/pws/webservices/retrievalservice.asmx?WSDL
