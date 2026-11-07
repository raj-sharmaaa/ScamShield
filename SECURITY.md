# Security Policy

## Supported versions

Security fixes are developed against the latest code on the `main` branch. Older deployments may not receive security fixes; update to the latest supported revision before reporting an issue as unresolved.

## Reporting a vulnerability

Please do **not** report suspected vulnerabilities in public GitHub issues, discussions, or pull requests.

1. If GitHub's **Security → Report a vulnerability** option is available for this repository, use it to submit a private report.
2. If private vulnerability reporting is not enabled, contact the repository maintainer privately through the contact options on the maintainer's GitHub profile. Do not publish exploit details while seeking a private contact route.
3. Include the affected component, impact, reproduction steps, and any relevant sanitized logs. Use a minimal proof of concept and avoid accessing or modifying other people's data.

Never include passwords, API keys, provider identity tokens, database credentials, private user messages, or other personal data in a report. Redact secrets from screenshots and logs.

## What to expect

The maintainer will review the report, may ask for additional information, and will work to validate the issue and determine an appropriate fix or mitigation. Please allow reasonable time for investigation. No fixed response or remediation SLA is currently offered.

When a fix is available, coordinated disclosure and a public security advisory may be used where appropriate. Please coordinate public disclosure with the maintainer rather than publishing an unpatched exploit.

## Scope

Reports are especially useful for issues involving authentication and account linking, user-data isolation, unsafe URL or message handling, API access controls, dependency vulnerabilities, and deployment configuration.

This policy does not authorize security testing against infrastructure or accounts that you do not own or have explicit permission to test.
