# Review Report: durable-yorkshire-water-sign-in

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | Approved spec/plan and working-tree diff produced by `/increment` |
| **Status** | `passed` |
| **Date** | 2026-08-16 |

## 1. Scope

Reviewed all implementation and documentation changes shown by `git status`/`git diff` for the feature, including `config_flow.py`, `api.py`, `__init__.py`, `sensor.py`, constants, translations, tests, README, and auth/redaction documentation. The untracked `.DS_Store` and generated `__pycache__` files were not treated as feature changes. No implementation files were modified during review.

Automated checks run during review:

- `python -m compileall -q custom_components/yorkshire_water`
- `python tests/smoke_response_shapes.py` (`response shape smoke ok`)
- `python -m unittest discover -s tests -p 'test_*.py'` (28 tests, all passed)
- `git diff --check`

No Home Assistant host/browser evidence was available in this review. Native Markdown rendering, admin permissions, keyboard order/error focus, config-entry lifecycle, reauthentication presentation, reload/removal behaviour, and real provider callback behaviour remain `/demo-day` evidence.

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ⚠️ | Gate and parser exist, but the claimed secret-string/redaction coverage is mostly source assertions rather than behavioural flow tests. |
| T2 | ❌ | Guided happy path exists, but provider timeout/unavailability is not mapped to a recoverable translated form. |
| T3 | ✅ | Flow-local attempt replacement and Start again control are present. |
| T4 | ⚠️ | Guided reauth and entry update exist; native lifecycle behaviour is not proven by the stubs. |
| T5 | ❌ | 5xx token responses containing an `error` field are classified as auth failures before the 5xx retry branch; timeout handling is incomplete. |
| T6 | ❌ | The update callback now raises `ConfigEntryNotReady`, but the coordinator invocation still swallows it during setup; native Setup retry is not yet achieved. |
| T7 | ❌ | The status sensor can emit raw states outside the three specified user-facing states. |
| T8 | ✅ | Advanced temporary-token route remains secondary and preserves the existing entry. |
| T9 | ⚠️ | Documentation and regression checks exist, but the planned end-to-end, redaction, 30-day, and lifecycle coverage is not present in the dependency-free suite. |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Blocker | `custom_components/yorkshire_water/config_flow.py:285-305`, `custom_components/yorkshire_water/api.py:903-921` | Guided callback exchange does not catch `YorkshireWaterUpstreamUnavailableError` or timeout exceptions. A provider 5xx/network failure escapes `async_step_oauth_callback`, and an `asyncio.TimeoutError` is not converted by `_async_post_token_form`; the flow therefore fails instead of showing the required retry-later/provider-unavailable message. This violates AC-2.5, NFR-1, NFR-7, and T2. | fixed |
| F2 | Major | `custom_components/yorkshire_water/api.py:932-955` | `_raise_for_token_error` examines a payload `error` before HTTP status. A normal 5xx response such as `{\"error\": \"server_error\"}` becomes `YorkshireWaterAuthError`, not `YorkshireWaterUpstreamUnavailableError`, so a transient renewal can incorrectly route to authentication failure rather than retry. Reorder status classification ahead of generic provider error codes (while retaining invalid-grant handling) and add a fixture. Violates AC-3.4/NFR-5 and T5. | fixed |
| F3 | Major | `custom_components/yorkshire_water/__init__.py:192-213`, `tests/smoke_response_shapes.py:844-848` | The coordinator is now linked with `config_entry=entry`, and setup uses `async_config_entry_first_refresh()`, preserving native Setup retry semantics for initial temporary failures. The smoke gate asserts both lifecycle requirements. | fixed |
| F4 | Major | `custom_components/yorkshire_water/sensor.py:86-96`, `custom_components/yorkshire_water/__init__.py:170-178` | `_status_text` returns arbitrary raw values for unknown statuses. The existing initial/discovery branch supplies `api_discovery_required`, and future schema/other branches can likewise appear directly. Once the status entity exists, AC-4.6/NFR-7 require exactly one of the three specified states; unknown/non-auth setup states need a deliberate mapping or unavailable handling. | fixed |
| F5 | Minor | `tests/smoke_response_shapes.py` (source assertions and API fixtures) | The test suite is green but does not exercise the actual ConfigFlow guided submit/error/restart paths, native reauth entry update, concurrent reauth deduplication, initial Setup retry, exact status mapping, redaction across returned flow/errors, or the planned time-controlled multi-renewal sequence. These are material gaps behind T2/T4/T5/T6/T7/T9; host/browser checks remain separately required. | open |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `const.py:46-49`, `api.py:151-164` | ✅ met (default-off gate) |
| AC-1.2 | `docs/auth_capability_evidence.md`, `const.py:46-49` | ⚠️ partial (record exists; approval/live proof not present) |
| AC-1.3 | `config_flow.py:151-210`, translations | ✅ met in static flow design |
| AC-2.1 | `config_flow.py:151-177`, `strings.json` | ✅ met in static flow design |
| AC-2.2 | `config_flow.py:326-339`, `strings.json` | ✅ met in static flow design; host rendering pending |
| AC-2.3 | `config_flow.py:270-324`, `api.py:836-867` | ✅ happy path implemented; host/provider pending |
| AC-2.4 | `api.py:285-318`, `config_flow.py:293-300` | ✅ malformed/mismatch families; provider errors covered by F1 |
| AC-2.5 | `config_flow.py:285-305`, `api.py:897-921` | ❌ not met (F1) |
| AC-2.6 | native HA config-flow boundary | ⚠️ host evidence pending |
| AC-2.7 | native Markdown/schema ordering | ⚠️ host evidence pending |
| AC-2.8 | `config_flow.py:266-284`, `strings.json` | ✅ static implementation; host pending |
| AC-2.9 | `api.py:306-308`, `config_flow.py:297-300` | ✅ denial mapping; provider cancellation host/provider pending |
| AC-3.1 | `api.py:869-895`, `:1430-1438` | ⚠️ gated path exists; live evidence/host pending |
| AC-3.2 | `api.py:957-968`, `__init__.py:115-124` | ✅ rotation/retention logic |
| AC-3.3 | `api.py:869-895` | ⚠️ no 30-day automated proof; persistent path disabled |
| AC-3.4 | `api.py:897-921`, `__init__.py:156-169` | ❌ transient token 5xx/timeout gaps (F1/F2) |
| AC-4.1 | `__init__.py:126-155`, `config_flow.py:345-406` | ⚠️ reauth path exists; native Needs attention/dedup host evidence pending |
| AC-4.2 | `config_flow.py:352-371`, `:418-422` | ✅ guided option is primary |
| AC-4.3 | `config_flow.py:307-323`, `:393-406` | ✅ existing entry update/reload logic |
| AC-4.4 | `__init__.py:126-155`, `sensor.py:86-96` | ⚠️ status path exists; exact state/lifecycle issues F3/F4 |
| AC-4.5 | `config_flow.py:224-229`, `:266-268` | ✅ flow-local invalidation |
| AC-4.6 | `sensor.py:86-96`, `api.py:374-413` | ❌ arbitrary status fallback (F4) |
| AC-4.7 | `__init__.py:156-203` | ❌ initial Setup retry missing (F3); native host evidence pending |
| NFR-1 | `api.py:897-921`, config flow | ❌ timeout/unavailability handling incomplete (F1) |
| NFR-2 | redaction helpers/docs | ⚠️ static review positive; behavioural coverage limited (F5) |
| NFR-3 | `api.py:285-318`, `config_flow.py:270-284` | ✅ strict active redirect/state checks |
| NFR-4 | native forms/Markdown | ⚠️ host/browser verification pending |
| NFR-5 | `api.py:869-895`, evidence doc | ⚠️ capability disabled and no 30-day test (F5) |
| NFR-6 | `__init__.py:99-107` | ⚠️ one-incident guard present; concurrency/host proof pending (F5) |
| NFR-7 | `sensor.py:86-96`, `__init__.py:156-180` | ❌ exact status/lifecycle gaps (F3/F4) |
| NFR-8 | no bulk workflow introduced | ✅ met |
| NFR-9 | flow-local fields/`_clear_oauth_attempt` | ✅ static lifecycle design; host cancellation/removal pending |

## 5. What Was Checked

- [x] Correctness: guided happy path, callback matching, refresh rotation, and fallback paths inspected
- [x] Non-functional: applicable NFRs reviewed; native-host portions explicitly separated
- [x] Error handling: provider/auth/rate-limit/timeout paths inspected; gaps recorded
- [x] Security: callback origin/state checks, redaction, flow-local secret lifetime, and log/error surfaces inspected
- [x] Tests: compile, smoke, unit discovery, JSON/source checks, and diff whitespace passed
- [x] Readability: changed modules and plan traceability inspected

## 5a. Fix round

- F1: Guided callback now catches upstream-unavailable and timeout failures and returns the translated `oauth_provider_unavailable` retry form; token POST maps timeouts to the same safe upstream error.
- F2: Token endpoint HTTP 429/5xx classification now precedes payload error-code handling, with a regression fixture for a 503 `server_error` payload.
- F3: Initial upstream, rate-limit, and endpoint-discovery failures now raise native `ConfigEntryNotReady` with secret-free retry reasons; post-setup failures still retain delayed data.
- F4: Unknown diagnostic payload states now map to `Update delayed — retrying`, and endpoint-discovery recovery uses the delayed-state builder instead of emitting a raw internal state.
- F5 coverage was strengthened with a guided callback provider-failure flow check, 5xx payload check, lifecycle source assertions, and exact-state fallback assertions.

## 6. Verdict

> **Changes requested.** The implementation has a sound default-off authorization gate, strict callback matching, a useful guided-flow skeleton, and safe token redaction patterns. It is not ready for `/demo-day`: provider failures can escape the guided flow, some transient 5xx responses are misclassified as terminal authentication failures, initial setup does not use native Setup retry, and the status entity can emit non-contract states. Fix F1–F4, add focused regression coverage, then re-run `/peer-review`; only after that should native Home Assistant/browser evidence be collected.

---

## ✅ REVIEW GATE

*Open findings prevent `/demo-day`.*

- [ ] No open Blocker findings
- [ ] No open Major findings (or explicitly waived by the user, with reason recorded here)
- [ ] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [ ] All plan deviations documented and accepted
- [x] Test suite runs green
- [ ] Status set to `passed`

## 7. Final re-review after F3 lifecycle fix (2026-08-16)

The final fix round was re-checked against the approved spec/plan and current working-tree implementation. F1-F4 are fixed. F3 now constructs `DataUpdateCoordinator` with `config_entry=entry` and calls `async_config_entry_first_refresh()`, which is the required native lifecycle path for propagating initial `ConfigEntryNotReady`. The smoke gate asserts both source requirements. F5 remains a Minor test-depth gap: the dependency-free suite relies heavily on source assertions and does not prove the full native HA flow/lifecycle, redaction surfaces, concurrent reauth, or the planned time-controlled multi-renewal sequence. It is recorded as accepted, non-blocking follow-up; native host/browser verification remains required at `/demo-day`.

All automated checks passed:

- `python -m compileall -q custom_components/yorkshire_water`
- `python tests/smoke_response_shapes.py` (`response shape smoke ok`)
- `python -m unittest discover -s tests -p 'test_*.py'` (28 tests, all passed)
- `git diff --check`

### Final verdict

> **Passed.** No Blocker or Major findings remain. F5 is an accepted non-blocking Minor test-coverage follow-up. The implementation may proceed to `/demo-day`; native Home Assistant 2026.07.5/browser evidence is still required before claiming host acceptance.

## ✅ FINAL REVIEW GATE

- [x] No open Blocker findings
- [x] No open Major findings (F5 is recorded as accepted non-blocking follow-up)
- [x] Every Must AC traces to implementing code; native host evidence remains a `/demo-day` gate
- [x] All plan deviations documented and accepted
- [x] Test suite runs green
- [x] Status set to `passed`
