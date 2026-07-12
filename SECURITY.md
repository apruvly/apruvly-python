# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |
| < 0.1   | No        |

## Reporting a vulnerability

**Do not** report security issues through public GitHub issues, discussions, or pull requests.

Please use one of these private channels:

1. **GitHub private vulnerability reporting** (preferred):  
   https://github.com/apruvly/apruvly-python/security/advisories/new
2. Email: **security@apruvly.io**

Include as much of the following as you can:

- Affected version, tag, or commit SHA
- Description of the issue and why it is security-sensitive
- Steps to reproduce or a proof of concept
- Potential impact
- Any suggested mitigations

You can expect an acknowledgment within a few business days. If the report is confirmed, we will work on a fix and coordinate disclosure timing when appropriate.

## Scope

In scope: this Python client library (authentication handling, HTTP transport, webhook signature verification, and related packaging).

Out of scope: the Apruvly hosted API/service itself (report those via the Apruvly product security channels), third-party dependencies you add in your own application, and social-engineering reports.
