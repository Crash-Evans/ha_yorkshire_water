# QA Report: durable-yorkshire-water-sign-in

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | `http://homeassistant.local:8123`, approved spec and plan, deployed commit `a298232` |
| **Status** | `failed` |
| **Date** | 2026-08-16 |

## 1. Test Environment

- **App URL:** `http://homeassistant.local:8123`
- **Browser / viewport(s):** Fresh Playwright MCP Chrome session; desktop and mobile `390x844`.
- **Test data / accounts used:** Authenticated Home Assistant administrator; no Yorkshire Water credentials, second HA user, or provider renewal fixture.

The live runtime now serves the approved guided flow. The old beta schema is gone: the initial flow presents `guided` and `temporary_token` choices, and the guided callback step schema contains only required `oauth_callback_url` plus the generated link placeholders. UI-only journeys were tested at both viewports. Provider success, renewal, native reauth, and status-entity paths remain untestable without a valid provider account/fixture.

## 2. Acceptance Criteria Verification

| Spec ID | Steps performed and observed result | Result |
|---|---|---|
| AC-1.1 | Opened setup; guided-first form makes no persistent/unattended authorization claim. | ✅ pass |
| AC-1.2 | Looked for maintainer evidence-review surface; none is exposed in the customer browser flow. | ⏸ blocked |
| AC-1.3 | Opened guided-first flow; it offers guided sign-in and does not promise unattended persistence. | ✅ pass |
| AC-2.1 | Initial form requests sign-in method plus optional account/meter references; no password, token, code, or verifier field. | ✅ pass |
| AC-2.2 | Guided step shows `Open Yorkshire Water sign-in (opens a new tab)`, the same selectable URL, and return/paste instructions. Link has `target=_blank` and `rel=noreferrer noopener`. | ✅ pass |
| AC-2.3 | No valid provider callback/credentials available for connection completion. | ⏸ blocked |
| AC-2.4 | Submitted `not-a-url`; callback remained available with `Paste the complete final callback URL from Yorkshire Water`. | ✅ pass |
| AC-2.5 | No provider outage/timeout fixture available. | ⏸ blocked |
| AC-2.6 | Admin setup works; no second non-admin session supplied. | ⏸ blocked |
| AC-2.7 | Focused the external link, tabbed to the selectable URL link, then tabbed to the callback textbox; native labels/order observed. | ✅ pass |
| AC-2.8 | Invalid callback produced `Start again`; with a callback value and Start again checked, submit generated a fresh authorization URL with new challenge/state and removed the checkbox. | ✅ pass |
| AC-2.9 | No provider denial/cancellation response available. | ⏸ blocked |
| AC-3.1 | No provider-supported connected entry or expiry fixture. | ⏸ blocked |
| AC-3.2 | No replacement-token renewal fixture. | ⏸ blocked |
| AC-3.3 | No 30-day provider-supported test/evidence. | ⏸ blocked |
| AC-3.4 | No transient provider failure fixture. | ⏸ blocked |
| AC-4.1 | No Yorkshire Water entry/reauth incident exists in the live integration list. | ⏸ blocked |
| AC-4.2 | No reauth flow available to inspect. | ⏸ blocked |
| AC-4.3 | No valid provider auth/entry available to verify retention. | ⏸ blocked |
| AC-4.4 | No reauth flow available to cancel/fail. | ⏸ blocked |
| AC-4.5 | Start-again behavior was verified in initial setup; existing-entry preservation cannot be tested without an entry. | ⏸ blocked |
| AC-4.6 | No diagnostic status entity exists without a completed entry. | ⏸ blocked |
| AC-4.7 | No completed entry exists for Loaded/Setup retry/Needs attention inspection. | ⏸ blocked |
| AC-5.1 | No existing bearer-token entry supplied. | ⏸ blocked |
| AC-5.2 | No existing bearer reauth entry supplied. | ⏸ blocked |
| AC-5.3 | No migration fixture supplied. | ⏸ blocked |
| AC-6.1 | Hierarchy works: guided is selected first; choosing the second option opens `Use a temporary access token (advanced)` with an explicit temporary-lifetime warning. The follow-up fix supplies descriptive radio labels for both choices. | ✅ pass |
| AC-6.2 | No valid temporary token supplied. | ⏸ blocked |
| AC-6.3 | No fallback entry available to expire. | ⏸ blocked |
| AC-6.4 | Guided form/callback step contains no OAuth, PKCE, token, verifier, scope, or refresh-token terminology. | ✅ pass |

### Browser-observable NFRs

| Spec ID | Steps performed and observed result | Result |
|---|---|---|
| NFR-1 | Initial and callback forms became interactive promptly at desktop and mobile sizes; provider timeout not tested. | ✅ pass (local UI) / ⏸ provider timeout blocked |
| NFR-2 | Guided UI requests no secrets and console stayed clean; retained evidence/log redaction cannot be browser-verified here. | ⏸ blocked |
| NFR-3 | Malformed callback rejected; Start again generated a fresh attempt. Replay/matching callback not completed. | ⏸ blocked |
| NFR-4 | External link, callback, and auth-method controls are labelled and keyboard order was verified at desktop and mobile sizes. | ✅ pass (browser UI) |
| NFR-5 | No 30-day provider fixture/evidence. | ⏸ blocked |
| NFR-6 | No connected auth incident for duplicate-reauth test. | ⏸ blocked |
| NFR-7 | Correctable callback and Start again families observed; provider denial, timeout, lifecycle, and diagnostic status unavailable. | ⏸ blocked |
| NFR-8 | Spec marks authentication workflow scale N/A. | ✅ pass (spec N/A) |
| NFR-9 | Fresh start visibly changes the authorization attempt; full flow cleanup after completion/entry removal unavailable. | ⏸ blocked |

## 3. Exploratory Findings

| # | Severity | Steps to reproduce | Expected vs. observed | Status |
|---|---|---|---|---|
| B1 | Minor | Add integration → Yorkshire Water; inspect the initial `Sign-in method` radiogroup at desktop or mobile size | The prior deployed form exposed raw `guided` and `temporary_token` names. The follow-up fix replaces the legacy `vol.In` field with labelled native selector options; rerun browser verification after deployment. | fixed |

## 4. Console & Network

- Browser console after page load and all tested setup/callback/fallback actions: **0 messages, 0 errors, 0 warnings**.
- Flow POSTs and cleanup DELETEs returned HTTP 200.
- Guided flow response schema: required `oauth_callback_url`; placeholders for the labelled external Markdown link and selectable authorization URL.
- Malformed callback response: `oauth_callback_invalid`, with optional `oauth_start_again`.
- Start again response: fresh callback form with a new authorization challenge/state.
- Temporary fallback response schema: `bearer_token` and `token_response_json`; empty submit returns `invalid_auth`.
- No provider request was completed because no valid Yorkshire Water credentials were supplied.

## 5. Verdict

> **“The deployed runtime serves the approved guided and advanced fallback journeys, and the browser-observable callback/restart behavior works at desktop and mobile sizes. The radio-label defect is fixed in the follow-up commit, but provider-backed connection, renewal, native reauthentication/status, and 30-day durability criteria remain unverified without a valid provider fixture.”**

Deploy the follow-up radio-label fix, then rerun the provider-backed and native lifecycle/status checks with approved test data. Do not mark the QA gate passed while Must-story criteria remain blocked.

---

## ✅ QA GATE

- [ ] Every Must-story acceptance criterion verified in the real browser and passed
- [ ] Every browser-observable NFR verified and passed
- [x] No open Blocker or Major bugs (one Minor finding listed)
- [x] Browser console free of errors on the tested flows
- [x] Tested at desktop and mobile viewport sizes
- [ ] Status set to `passed`
