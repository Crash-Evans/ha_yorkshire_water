# Persistent authorisation evidence

Persistent Yorkshire Water authorisation is disabled by default. It may only
be enabled after a redacted live capture proves both of these behaviours:

1. The provider issues a refresh token for the requested authorisation.
2. That refresh token successfully renews access after the original access
   token expires.

Record only the provider, tested date, requested scope names, HTTP status/error
codes, token-presence booleans, expiry timing, and the final renewal result.
Never retain authorization codes, code verifiers, callback URLs containing
secrets, cookies, passwords, access tokens, refresh tokens, or full responses.

The code-level capability remains off until an approved evidence identifier is
set alongside an explicit approval. A provider rejection must leave the guided
reauthentication path available and must not be presented as durable access.
