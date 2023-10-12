# Serverless Operational Review Tool Versions

- **Version 1.2.0**
  - SAM CLI version 1.94 or higher is required to deploy this tool as all backend compute is using Python 3.11!
  - Reporting for all Lambda functions agregates all data into single report file.
  - Direct passing from JSON to HTML
  - Event Source Mappings have its own subsection inside Reviewed function configurations and provide almost all information depending on the type of the event source.

- **Version 1.1.1**
  - Reporting on all or selected Lambda functions in the region the tool is deployed to.
  - Generating 1 report per up to 50 Lambda functions due to CLI limitations.
  - Backend Lambda functions using Python 3.10.
