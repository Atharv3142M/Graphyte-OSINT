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
- Guard outbound network requests against SSRF targets (private IPs, localhost, and link-local ranges are blocked in `backend/api.py`).
- Avoid introducing hardcoded credentials.
- Ensure secrets are read from environment variables or secure stores only.
- Add tests for security-relevant changes when practical.
- Module subprocesses must not write secrets to stdout (only the final JSON result line belongs on stdout).

## Responsible use

Graphyte OSINT performs active and passive reconnaissance against user-supplied targets. Deploy only on systems and networks you are authorized to assess. Contributors should not add modules that exfiltrate local files, execute arbitrary shell commands from user input, or bypass the platform SSRF policy.
