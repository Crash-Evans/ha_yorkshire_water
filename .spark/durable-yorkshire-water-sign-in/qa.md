# QA Report: durable-yorkshire-water-sign-in

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | `http://homeassistant.local:8123`, approved spec and plan |
| **Status** | `failed` |
| **Date** | 2026-08-16 |

## 1. Test Environment

- **App URL:** `http://homeassistant.local:8123`
- **Browser / viewport(s):** Fresh Playwright MCP Chrome session; desktop and mobile `390x844`.
- **Test data / accounts used:** Authenticated Home Assistant administrator; no Yorkshire Water credentials/provider fixture.

This is a fresh rerun after the runtime update opportunity. Home Assistant overview and `/config/integrations` load successfully. The live Yorkshire Water flow remains the old beta flow; the approved guided implementation is not loaded.

## 2. Acceptance Criteria Verification

`pass` means directly observed in the live browser. `fail` means the live browser contradicted the criterion. `blocked` means the required provider credential, second account, existing entry, or approved flow was unavailable.

| Spec ID | Steps performed and observed result | Result |
|---|---|---|
| AC-1.1 | Opened Add integration → Yorkshire Water; `Experimental: request offline access / refresh token` is visible. | ❌ fail |
| AC-1.2 | Searched the live setup for capability/evidence review; none exists. | ⏸ blocked |
| AC-1.3 | Opened supported sign-in; approved guided unsupported-persistence messaging is absent. | ⏸ blocked |
| AC-2.1 | Setup form visibly requests temporary token, token JSON, callback, OAuth code, and PKCE verifier; description mentions DevTools. | ❌ fail |
| AC-2.2 | No descriptively labelled Yorkshire Water external sign-in link or selectable generated URL is present. | ❌ fail |
| AC-2.3 | Submitted callback-only fake URL; old form returned `Enter valid experimental OAuth callback/code details`, with no connection. | ❌ fail |
| AC-2.4 | Submitted empty setup and observed `Enter a valid access token`; callback journey is not the approved correctable flow. | ❌ fail |
| AC-2.5 | No provider journey/fixture available for timeout or retry-later test. | ⏸ blocked |
| AC-2.6 | Admin setup is accessible; no second non-admin session was supplied. | ⏸ blocked |
| AC-2.7 | No guided link exists, so required link → callback → submit keyboard order cannot be verified. | ❌ fail |
| AC-2.8 | No active guided attempt or `Start again` control exists. | ❌ fail |
| AC-2.9 | No provider denial/cancellation journey is available. | ⏸ blocked |
| AC-3.1 | No connected provider-supported entry/fixture is available for token-expiry renewal. | ⏸ blocked |
| AC-3.2 | No persistent authorization fixture/evidence is available. | ⏸ blocked |
| AC-3.3 | 30-day unattended run cannot be performed without provider fixture/evidence. | ⏸ blocked |
| AC-3.4 | No transient provider-failure fixture is available. | ⏸ blocked |
| AC-4.1 | No Yorkshire Water entry or native reauth incident is present in the live integration list. | ⏸ blocked |
| AC-4.2 | No reauth flow is available to verify guided-primary hierarchy. | ⏸ blocked |
| AC-4.3 | No valid provider auth/entry is available to verify retention. | ⏸ blocked |
| AC-4.4 | No reauth flow is available to cancel/fail. | ⏸ blocked |
| AC-4.5 | No `Start again` action is available. | ⏸ blocked |
| AC-4.6 | No Yorkshire Water diagnostic status entity is available. | ⏸ blocked |
| AC-4.7 | No Yorkshire Water entry is available to inspect Loaded/Setup retry/Needs attention lifecycle. | ⏸ blocked |
| AC-5.1 | No existing bearer-token Yorkshire Water entry is present. | ⏸ blocked |
| AC-5.2 | No existing bearer entry is present for next-reauth hierarchy. | ⏸ blocked |
| AC-5.3 | No migration fixture is present. | ⏸ blocked |
| AC-6.1 | All token/JSON/OAuth fields are directly exposed in the first form; no guided-primary/advanced-fallback hierarchy. | ❌ fail |
| AC-6.2 | No valid fallback token supplied. | ⏸ blocked |
| AC-6.3 | No fallback entry available to expire. | ⏸ blocked |
| AC-6.4 | Primary live form exposes OAuth, PKCE, token, verifier, refresh-token/offline-access and DevTools terminology. | ❌ fail |

### Browser-observable NFRs

| Spec ID | Steps performed and observed result | Result |
|---|---|---|
| NFR-1 | Integrations and old setup form became interactive promptly at desktop/mobile; approved changed form absent. | ⏸ blocked |
| NFR-2 | No secret values entered; live form explicitly requests secret-bearing values and DevTools extraction. | ❌ fail |
| NFR-3 | Fake callback produced old generic experimental validation; active-attempt binding not available. | ⏸ blocked |
| NFR-4 | Existing controls are labelled, but changed guided form and link order are absent. | ⏸ blocked |
| NFR-5 | No provider fixture/evidence for 30-day reliability. | ⏸ blocked |
| NFR-6 | No connected auth incident for duplicate-reauth test. | ⏸ blocked |
| NFR-7 | No feature lifecycle/status entity; old generic validation only. | ⏸ blocked |
| NFR-8 | Spec marks authentication workflow scale N/A. | ✅ pass (spec N/A) |
| NFR-9 | No approved guided flow available for cleanup test. | ⏸ blocked |

## 3. Exploratory Findings

| # | Severity | Steps to reproduce | Expected vs. observed | Status |
|---|---|---|---|---|
| B1 | Blocker | Authenticated HA → Settings → Devices & services → Add integration → Yorkshire Water | Expected approved guided flow. Observed pre-feature beta flow with direct token/JSON/OAuth fields and DevTools wording. Live API response schema contains `bearer_token`, `token_response_json`, `oauth_callback_url`, `oauth_authorization_code`, `oauth_code_verifier`, and `oauth_request_offline_access`. | open |
| B2 | Major | Submit empty form or callback-only fake URL | Expected guided actionable callback validation/restart. Observed old `invalid_auth` / `Enter valid experimental OAuth callback/code details`; no guided attempt or restart. | open |

## 4. Console & Network

- Browser console after page load and form submissions: **0 messages, 0 errors, 0 warnings**.
- Flow POSTs returned HTTP 200, but the response is the old `user` schema rather than the approved guided `auth_method` flow.
- No provider request was made because no valid provider credentials were supplied and the approved flow was unavailable.

## 5. Verdict

> **“Not ready to demo. After a fresh browser run, the host remains healthy and the console is clean, but the live Yorkshire Water integration still serves the pre-feature beta form. The guided sign-in, callback/recovery, fallback hierarchy, native reauthentication, and status surfaces cannot be accepted.”**

The runtime/deployment still needs to load the approved implementation. Rerun `/demo-day` only after the live flow schema changes from the old token/OAuth fields to the approved guided journey.

---

## ✅ QA GATE

- [ ] Every Must-story acceptance criterion verified in the real browser and passed
- [ ] Every browser-observable NFR verified and passed
- [ ] No open Blocker or Major bugs
- [x] Browser console free of errors on the tested flows
- [x] Tested at desktop and mobile viewport sizes
- [ ] Status set to `passed`
