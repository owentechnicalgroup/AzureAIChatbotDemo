## FEATURE:

The goal of this feature is to simplify the logging logic and separate the concerns into simple application logs and AI Observability implemented in the AI chat bot. The in the first phase we will focus on application logging. We will cover conversation observability in a future phase, so keep that in mind when making these changes.

- Implement the Azure Monitor Open Telemetry using the already configured connection to Application Insights
- For this first phase, implement basic logging for
- Correlated logs for startup activities
- Basic logging for informational logging
- Exception logs for error handling
- AI Conversation Monitoring using information logging with a special attribute indicating it is a conversation.

## EXAMPLES:

In the `examples/` folder, there is a README for you to read to understand what the example is all about and also how to structure your own README when you create documentation for the above feature.

- `examples/opentelemetry-azure-monitor-python` - This example has example Python code to help implement Opentelemetry
- `examples/opentelemetry-python` - More python code showing how to implement Opentelemetry

## DOCUMENTATION:

Microsoft OpenTelemetry documentation: https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-enable?tabs=python
Azure Monitor Opentelemetry Distro client library for Python: https://learn.microsoft.com/en-us/python/api/overview/azure/monitor-opentelemetry-readme?view=azure-python

## OTHER CONSIDERATIONS:

- Logging structure compatible with Azure Application Insights
- Code should be fixed so that the separate concens for logging and conversation monitoring so that they may be ported to other platforms in the future
