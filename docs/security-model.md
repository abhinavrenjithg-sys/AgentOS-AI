# Security model and limits

- Local development is single-user and unauthenticated. Do not expose it to an untrusted network.
- The reader accepts HTTP(S), rejects local hostnames, resolves destinations and rejects non-global IPs, rechecks redirects, limits redirects, request duration, and response size.
- Retrieved text is treated as untrusted data. It is not passed into tool selection or execution.
- Tools are a closed registry represented by the Pydantic `Tool` literal. No shell, arbitrary Python, or arbitrary JavaScript tool exists.
- Email is a local draft only. No send integration exists.
- Generated artifact names are controlled by the server, and download paths are checked against the artifact root.
- Secrets are not part of workflow inputs or logs. Configure provider credentials via environment variables.

These are MVP safeguards, not a production security boundary. DNS rebinding remains possible between validation and connection; use a controlled egress proxy/network policy and isolated browser worker before accepting untrusted users. Add accounts, workspace authorization, rate limits, retention, encryption, and audit-event storage before production.
