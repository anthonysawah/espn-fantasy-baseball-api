# Security Policy

## Reporting a vulnerability

If you believe you've found a security issue in
`espn-fantasy-baseball-api`, **please do not open a public issue**.
Instead, report it privately via GitHub's
[**Security → Report a vulnerability**](https://github.com/anthonysawah/espn-fantasy-baseball-api/security/advisories/new)
flow.

We'll acknowledge within 72 hours and aim to patch within 14 days.

## Scope

This library is a thin HTTP client. In-scope issues include:

- Credential leakage (e.g. logging `espn_s2` or `SWID`).
- SSRF / open-redirect style flaws in URL construction.
- Injection / deserialization vulnerabilities in the parsing layer.
- Unsafe handling of the `X-Fantasy-Filter` header or other
  user-supplied data.

Out of scope:

- Vulnerabilities in `requests`, Python, or the operating system.
- Flaws in ESPN's own services.

## Handling cookies

Your `espn_s2` cookie grants full access to your ESPN account. **Treat
it like a password**:

- Don't commit it to source control.
- Don't paste it into public issues, PRs, or support channels.
- Prefer environment variables or a secrets manager.
- Rotate it (by logging out and back in) if you suspect exposure.

If a PR accidentally includes a cookie, we will:

1. Rewrite history to remove it (if not yet merged).
2. Notify the submitter to revoke the cookie immediately.
3. Never publish the value.
