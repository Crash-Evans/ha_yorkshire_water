# Yorkshire Water Portal Capture Notes (maintainer-only)

Yorkshire Water endpoint support is still being discovered. This page is for maintainer-only redacted captures; it is not the supported user setup guide. Users should use the guided Home Assistant sign-in and must not use browser developer tools to obtain tokens.

## What To Capture

When an authorised maintainer is collecting provider evidence, use a disposable test account and browser developer tools only to identify:

- Authentication flow and token/session lifetime
- Whether requests use an `Authorization` header, cookies, CSRF tokens, or OAuth
- Account/customer discovery requests
- Meter discovery requests
- Current consumption or current meter reading requests
- Daily usage requests
- Monthly or custom-period usage requests, if present

## Safety

- Do not share raw authorization headers, cookies, session tokens, customer references, account IDs, or meter IDs.
- Redact sensitive values before opening GitHub issues.
- Do not commit captured responses containing personal data.
- Prefer sharing request/response schemas with fake IDs and representative numeric values.

## Useful Debugging

Enable Home Assistant debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.yorkshire_water: debug
```

The integration redacts known sensitive fields from its own debug logs, but browser captures are not automatically redacted.

Do not enable persistent authorization from a capture alone. Follow
`docs/auth_capability_evidence.md` and retain only the secret-free decision
record; the runtime capability remains disabled until the evidence is approved.
