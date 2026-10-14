# Credential SDK cleanup

Baseline: `6ce5a135830ff18fa5a3b6e56bc7573ae479b4ce` (python-sdk PR #142).
Server reference: browserctrl master `cc9109ca5fc144b1b4e20498bbe8c90513433c89`.

## Changes and observable differences

- Fill source/name rules, field counts and byte limits, selector uniqueness,
  page-target conflicts, allowed-origin syntax, vault entry policies and
  1Password name/reference limits are validated by the API. They no longer
  have a second handwritten implementation in this SDK.
- Invalid policy inputs can now make an HTTP request. Errors retain the API's
  HTTP status, optional code, retryable flag and details. A schema rejection
  may have no machine code; callers must not require `invalid_request` for
  every invalid input. Basic request-shape checks remain local.
- Vault create/update serialization retains omission versus explicit entry
  removal (`null` / `None`). Exact-name lookup and UUID-name fallback remain.
- 1Password source conflicts with secrets, environment variables or vault
  entries are rejected by the control API. Process requests with any secret
  source still go through that API; uncertain outcomes remain non-retryable.
- Gemini support is scoped to `CredentialFillTool` and
  `FILL_CREDENTIAL_TOOL_GEMINI`. The unreleased general schema converters,
  related helper types and Gemini declarations on unrelated tools are removed.
  The fill declaration reuses the shared descriptions and parameter names.
- Tests of removed local policies are replaced by API rejection/serialization
  coverage. Encryption, TOTP, routing, partial-create errors, secret delivery,
  startup binding preservation, and tool normalization coverage remain.

## Deliberately retained

- Local encryption, key verification, UTF-8/size/NUL value checks, exact
  server-provided encryption contexts, and errors after partial creation.
- The complete local TOTP validator. The API cannot inspect an encrypted seed;
  removing it would delay malformed-seed errors until use.
- Existing stored-secret shorthand/name/version checks and SDK launch/routing
  restrictions. This cleanup does not change the older secret API wholesale.
- The LLM tool still binds its session in application code and never exposes
  1Password origin selection to a model.
- Both synchronous and asynchronous managers, TypedDict inputs and legacy
  Pydantic request objects. Pydantic shape/unknown-member checks remain;
  shared serializers retain aliases, nested nulls and response-entry projection.

## Validation

- Python 3.12: 993 tests passed, including mypy/Pyright fixtures; Ruff and
  wheel/sdist builds passed.
- Python 3.8.20: 988 passed, four typing tests skipped, and one unrelated
  CAPTCHA localhost integration test timed out. That test plus the complete
  credential/secrets/vault/tool subset passed on retry (300 tests). The
  cryptography dependency emitted its Python 3.8 deprecation warning.
- Compared 44 request cases from both SDKs against the actual Zod schemas and
  metadata validators loaded from the immutable server revision above. Valid
  requests agree on their wire representation; invalid policy inputs are
  refused by the server validators or local Python shape checks.
- Executed master's source-merging function: 1Password clashes with vaults or
  explicit secrets are refused; disjoint variables are accepted.
- Contract comparison is source-level validation, not a running API/database,
  browser session or live 1Password end-to-end test. Those live checks were
  not repeated for this cleanup.
