# Security Policy

## Supported versions

Security fixes are applied to the latest `main` branch.

## Reporting a vulnerability

Do not report vulnerabilities in public issues.

Report privately with:

- Affected component(s)
- Reproduction steps or proof of concept
- Potential impact
- Suggested remediation (optional)

Until a dedicated security email is configured, open a private security advisory in GitHub for this repository.

## Response targets (best effort)

- Initial triage: within 72 hours
- Confirmation and severity: within 7 days
- Patch or mitigation target: depends on severity and complexity

## Secure development expectations

- Validate and sanitize all user input.
- Guard outbound network requests against SSRF targets.
- Avoid introducing hardcoded credentials.
- Ensure secrets are read from environment variables or secure stores only.
- Add tests for security-relevant changes when practical.
