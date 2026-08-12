# Security Policy

## Sensitive information

Do not report or commit API keys, QQ bot credentials, GitHub tokens, private
chat logs, or local filesystem paths. Use GitHub Security Advisories for a
security issue in the code, or open a minimal issue without sensitive data for
operational problems.

LLM credentials must be supplied through process environment variables or
GitHub Actions Secrets. They must never be stored in tracked configuration,
generated Pages files, browser-side code, logs, screenshots, issues, or pull
requests. See [LLM configuration and secret management](docs/llm-configuration.md)
for setup instructions and the pre-commit checklist.

Forks do not inherit repository Secrets. Contributors must use their own API
credentials for local testing and must keep changes reproducible when no LLM
credential is available.

## AutoClaw

The AutoClaw integration intentionally accepts only a fixed command set and
must never be changed to pass arbitrary QQ text to a shell.

## Reporting and credential exposure

Report code vulnerabilities privately through GitHub Security Advisories.
Never include a live credential in the report. If a credential is exposed,
revoke or rotate it at the provider immediately, review its usage, remove it
from public artifacts, and only then consider Git history cleanup. Deleting a
commit does not invalidate a leaked credential.
