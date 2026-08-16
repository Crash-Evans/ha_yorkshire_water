# Spec: durable-yorkshire-water-sign-in

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-08-16 |
| **Ticket** | none |

## 1. Problem & Goal

- **Problem:** Yorkshire Water customers using the Home Assistant integration currently depend on access tokens that typically expire after about 15 minutes. Unless Yorkshire Water issues a usable refresh token, they must extract and paste another secret from browser developer tools, interrupting sensor updates and making the integration unsuitable for routine use.
- **Goal:** Let a Home Assistant administrator connect through a guided Yorkshire Water portal journey without developer-tool token extraction, keep updates running unattended when the provider supports persistent authorization, and recover through a guided journey when it does not.
- **Success signal:** In a verified provider-supported case, a configured integration updates unattended for 30 consecutive days across multiple access-token renewals unless Yorkshire Water revokes access; in a verified no-persistent-authorization case, the user can restore updates through guided portal login and callback submission without developer tools or manual token extraction.
- **Why now:** Authentication expires far sooner than the integration's normal operating life. Every sensor and historical-data feature loses practical value when routine updates require repeated secret extraction.

## 2. Target Users

- A Yorkshire Water smart-meter customer who administers their own Home Assistant instance and wants continuing water-usage updates.
- An existing beta user currently configured with a manually supplied bearer token who needs a supported recovery path at the next authentication failure.
- The integration maintainer who must enable only provider behaviours demonstrated by safely redacted live evidence.

## 3. Assumptions & Open Questions

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | Yorkshire Water may support persistent authorization and repeated token renewal. | Not assumed. Persistent authorization remains evidence-gated until safely redacted live evidence proves both issuance and successful renewal. |
| A2 | Yorkshire Water may revoke access during the 30-day success period. | Provider revocation is an accepted boundary; the integration must detect it and start guided reauthentication. |
| A3 | A callback URL can be copied from the completed portal journey without browser developer tools. | Accepted product flow; raw authorization-code and verifier entry is not part of the supported journey. |
| A4 | Existing bearer-token installations need immediate migration. | Rejected. They migrate through the supported journey at their next required reauthentication. |
| A5 | No constitution or active quality lens applies. | Confirmed for this feature. |

## 4. User Stories

### US-1 (Must): Evidence-gated authorization capability

> As the integration maintainer, I want persistent authorization enabled only after provider behaviour is safely verified, so that users are not promised an unsupported unattended connection.

**Acceptance criteria:**

- [ ] AC-1.1: Given no approved redacted evidence that Yorkshire Water issues a refresh token and accepts its exchange, when a user starts supported sign-in, then the flow does not claim or enable persistent authorization.
- [ ] AC-1.2: Given a safely redacted capture from the real provider, when the capability decision is reviewed, then the evidence records whether persistent access was requested, whether a refresh token was issued, and whether renewal succeeded after access-token expiry, without retaining any secret value.
- [ ] AC-1.3: Given evidence that persistent authorization is unsupported, when the supported journey is used, then the user is offered guided reauthentication and is not told that the connection will remain unattended.

### US-2 (Must): Guided portal sign-in

> As a Home Assistant administrator, I want to sign in through Yorkshire Water's portal and submit the final callback URL, so that I can connect without extracting tokens in browser developer tools.

**Acceptance criteria:**

- [ ] AC-2.1: Given the user starts supported sign-in, when the first form is shown, then it explains that Yorkshire Water portal login and a final callback URL are required and does not request an access token, authorization code, code verifier, or Yorkshire Water password.
- [ ] AC-2.2: Given the user proceeds, when the portal step is ready, then the native Home Assistant flow presents a descriptively labelled external Markdown link, "Open Yorkshire Water sign-in (opens a new tab)", displays the same destination as selectable URL text for manual copy, and instructs the user to keep Home Assistant open and return with the final callback URL.
- [ ] AC-2.3: Given the user completes portal login and submits a valid matching callback URL, when Yorkshire Water accepts the authorization, then the integration confirms connection and begins updating data.
- [ ] AC-2.4: Given the callback is missing or malformed, when it is submitted, then the callback field remains available for correction and a plain-language message asks the user to paste the complete final callback URL.
- [ ] AC-2.5: Given the portal or authorization service is unavailable or times out, when sign-in cannot complete, then the user is told to retry later, no incomplete authorization is treated as connected, and no secret or provider response detail is exposed.
- [ ] AC-2.6: Given a Home Assistant user is not an administrator, when they attempt to configure or reauthenticate Yorkshire Water, then native Home Assistant permissions prevent them from starting the authorization journey; visibility of the non-secret diagnostic status entity follows Home Assistant's normal entity permissions.
- [ ] AC-2.7: Given an active sign-in step is displayed, when the user navigates by keyboard, then standard Home Assistant controls allow them to reach and activate the descriptively named external link before the labelled callback URL field and submit action in logical task order; the displayed URL remains selectable for manual copying without a custom clipboard control.
- [ ] AC-2.8: Given a callback belongs to an expired or mismatched attempt, when it is submitted, then the user is told that the sign-in attempt is no longer valid and is offered "Start again", which invalidates the abandoned attempt before creating a new one.
- [ ] AC-2.9: Given Yorkshire Water denies or the user cancels authorization, when Home Assistant receives that outcome, then the user sees a plain-language denial or cancellation message and can start again without the provider's technical response being displayed.

### US-3 (Must): Unattended renewal when supported

> As a connected Yorkshire Water customer, I want authorization to renew without intervention when the provider supports it, so that my water data continues updating after short-lived access tokens expire.

**Acceptance criteria:**

- [ ] AC-3.1: Given verified provider support and a valid persistent authorization, when an access token expires, then the next scheduled update renews authorization and completes without asking the user to sign in again.
- [ ] AC-3.2: Given renewal succeeds and the provider supplies replacement authorization data, when a later access token expires, then the most recently supplied valid authorization is used and updates continue.
- [ ] AC-3.3: Given a connected integration is exercised for 30 consecutive days with provider access not revoked, when multiple access-token expiries occur, then scheduled data updates continue without user intervention.
- [ ] AC-3.4: Given a temporary provider or network failure during renewal, when a later scheduled retry succeeds before authorization becomes invalid, then the integration resumes without forcing reauthentication.

### US-4 (Must): Guided recovery when access cannot renew

> As a Home Assistant administrator, I want a clear reauthentication journey when persistent access is unavailable, invalid, or revoked, so that I can restore updates without deleting and recreating the integration.

**Acceptance criteria:**

- [ ] AC-4.1: Given authorization cannot be renewed because it is unavailable, rejected, expired, or revoked, when the integration detects the condition, then the integration entry uses Home Assistant's native "Needs attention" lifecycle presentation and reauthentication action, the diagnostic status entity shows "Sign-in required — data last updated <time>", and Home Assistant opens no more than one active reauthentication flow for that incident.
- [ ] AC-4.2: Given reauthentication is required, when the user opens the flow, then the guided portal and callback journey from US-2 is the primary option.
- [ ] AC-4.3: Given guided reauthentication succeeds, when the flow completes, then the existing integration entry is retained, reloads, and resumes updates without losing its account, meter, entities, or existing statistics.
- [ ] AC-4.4: Given reauthentication is cancelled or fails, when the user returns to Home Assistant, then the integration entry remains in native "Needs attention" state with its reauthentication action, the diagnostic status entity identifies the data as "Sign-in required — data last updated <time>", and a fresh attempt remains available without deleting the config entry.
- [ ] AC-4.5: Given the user chooses "Start again" after an abandoned, expired, cancelled, or mismatched attempt, when the new journey begins, then the previous attempt can no longer authorize the integration and the existing config entry remains intact.
- [ ] AC-4.6: Given the diagnostic status entity has been created, when the integration is current, retrying a temporary update failure, or waiting for sign-in, then that entity shows exactly one corresponding state—"Connected — data current", "Update delayed — retrying", or "Sign-in required — data last updated <time>"—and its `last_successful_update` attribute contains the latest successful-update timestamp, or is unavailable before the first successful update.
- [ ] AC-4.7: Given the integration entry is viewed, when setup has completed, initial setup is retrying after a temporary failure, or authentication needs user action, then Home Assistant shows its applicable native lifecycle presentation: "Loaded", "Setup retry" with the retry reason, or "Needs attention" with the native reauthentication action; no diagnostic entity is required before Home Assistant has completed platform setup and created it.

### US-5 (Should): Existing installation migration at reauthentication

> As an existing bearer-token user, I want to move to the supported sign-in journey when authentication next fails, so that migration is timely without disrupting a currently working installation.

**Acceptance criteria:**

- [ ] AC-5.1: Given an existing bearer-token installation is still updating, when this feature is installed, then it is not forced into immediate reauthentication.
- [ ] AC-5.2: Given that installation next requires reauthentication, when the reauthentication form opens, then guided portal sign-in is presented as the supported primary journey.
- [ ] AC-5.3: Given migration succeeds, when the entry reloads, then existing configuration, entity identity, and historical statistics are preserved.

### US-6 (Should): Explicit manual fallback

> As a beta user blocked from guided sign-in, I want the existing manual bearer-token route clearly labelled as a fallback, so that I can recover temporarily without mistaking it for durable sign-in.

**Acceptance criteria:**

- [ ] AC-6.1: Given the user opens setup or reauthentication, when authentication choices are presented, then guided Yorkshire Water sign-in is the primary action and manual entry is available only behind a secondary choice labelled "Use a temporary access token (advanced)".
- [ ] AC-6.2: Given a valid fallback token is submitted, when the integration reloads, then updates resume for that token's valid lifetime without changing account, meter, entity, or statistics identity.
- [ ] AC-6.3: Given the fallback token expires, when the integration detects expiry, then it returns to guided reauthentication rather than claiming persistent access.
- [ ] AC-6.4: Given the user follows the primary guided journey, when any supported-customer form is displayed, then it does not expose OAuth, PKCE, token JSON, scope, code-verifier, or refresh-token terminology.

## 5. Non-Functional Requirements

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Performance | Each local sign-in or reauthentication form becomes interactive within 2 seconds on a supported Home Assistant installation; provider waits longer than 30 seconds end in a recoverable timeout state. | `/demo-day` |
| NFR-2 | Security & privacy | Yorkshire Water passwords are never requested or stored; callback URLs, authorization codes, code verifiers, access tokens, and refresh tokens never appear in logs, diagnostics, status sensors, form errors, or retained evidence. | `/peer-review` + automated redaction tests |
| NFR-3 | Security & privacy | A callback is accepted only for the active matching sign-in attempt; expired, replayed, or mismatched callbacks do not update the configuration entry. | `/peer-review` + `/demo-day` |
| NFR-4 | Accessibility | Every changed native Home Assistant form can be completed using keyboard alone; every standard control has a programmatic label; the external Markdown link has a destination-specific accessible name and appears before the callback field and submit action in logical document order; validation preserves standard Home Assistant error-focus behaviour; and errors are identified in text rather than by colour alone. | `/look-and-feel` + `/demo-day` |
| NFR-5 | Reliability | The verified persistent path completes a 30-day unattended test across multiple renewals, including replacement authorization data, without losing configuration or entity identity. | `/demo-day` with time-controlled provider fixtures plus live evidence gate |
| NFR-6 | Reliability | Repeated coordinator failures for one authentication incident create at most one active reauthentication flow, and a successful retry resumes the existing entry without duplicate entities. | `/demo-day` |
| NFR-7 | Observability / ops | Native integration lifecycle presentation is limited to the applicable states in AC-4.7. Once created, the existing diagnostic status entity exposes exactly one state from AC-4.6 plus a non-secret `last_successful_update` timestamp attribute; before entity creation, the native integration lifecycle is the status surface. Provider denial/cancellation, correctable callback input, expired/mismatched attempts, and temporary provider failure each produce the distinct actionable message family defined in AC-2.4, AC-2.5, AC-2.8, and AC-2.9. | `/peer-review` + `/demo-day` |
| NFR-8 | Scale | N/A: authentication is scoped to one Home Assistant config entry and does not introduce a bulk-data workflow. | `/peer-review` |
| NFR-9 | Data lifecycle | Callback URLs, authorization codes, code verifiers, and sign-in state are discarded when the flow completes or is abandoned; removing the config entry removes its retained Yorkshire Water authorization material. | `/peer-review` + `/demo-day` |

## 6. Out of Scope

- Automated browser control or storing Yorkshire Water usernames, passwords, cookies, or multi-factor credentials.
- Enabling or promising persistent authorization before safely redacted evidence proves issuance and successful renewal.
- Removing the manual bearer-token fallback in this cycle.
- Forcing working existing installations to migrate immediately.
- Raw authorization-code or user-supplied code-verifier entry as part of the supported journey.
- Changes to account or meter discovery, consumption sensors, statistics import/repair, cost history, dashboards, or polling frequency.
- Circumventing provider revocation, access policy, rate limits, or unsupported scopes.
- Supporting providers other than Yorkshire Water.
- A custom frontend, dedicated clipboard button, or custom focus-management control for the sign-in link.
- Arbitrary persistent status labels or bespoke actions on the Home Assistant integration card; lifecycle and reauthentication presentation remain native.

## 7. Clarifications

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-08-16 | May the feature assume Yorkshire Water supports persistent authorization? | No. Safely redacted evidence capture is the first prerequisite; issuance and successful renewal must both be proven. |
| C2 | 2026-08-16 | What duration makes sign-in durable? | 30 days unattended across multiple access-token renewals, unless Yorkshire Water revokes access. |
| C3 | 2026-08-16 | Must the portal return automatically to Home Assistant? | No. Guided portal login followed by pasting the final callback URL is acceptable; developer tools and manual token extraction are not. |
| C4 | 2026-08-16 | What happens when persistent authorization is unsupported? | Provide guided reauthentication without developer tools and retain manual bearer-token mode as an explicitly labelled fallback. |
| C5 | 2026-08-16 | When do existing bearer-token installations migrate? | At their next required reauthentication, with no forced immediate migration. |
| C6 | 2026-08-16 | Is design review required? | Yes. The feature changes user-facing Home Assistant setup and reauthentication forms, so `/look-and-feel` remains required. |
| C7 | 2026-08-16 | What happens to existing data and identity during recovery or migration? | The existing config entry, account/meter configuration, entity identity, and historical statistics must be preserved. |
| C8 | 2026-08-16 | How are repeated failures and temporary outages distinguished from invalid authorization? | Temporary failures remain retryable; invalid, unavailable, or revoked authorization starts one guided reauthentication incident. |
| C9 | 2026-08-16 | How is the generated Yorkshire Water authorization destination presented? | In the native Home Assistant flow as a descriptively named external Markdown link plus the same URL as selectable text for manual copy; it is never an editable form value. |
| C10 | 2026-08-16 | How does a user recover from an abandoned or invalid sign-in attempt? | A visible "Start again" action invalidates the abandoned attempt, creates a fresh journey, and preserves the existing config entry. |
| C11 | 2026-08-16 | Which authentication route is visually and sequentially primary? | Guided Yorkshire Water sign-in is primary; temporary bearer-token entry sits behind an Advanced fallback and is named in plain language. |
| C12 | 2026-08-16 | Where does a user see lifecycle, authentication, and staleness status? | The integration entry uses native Home Assistant lifecycle and reauthentication presentation. Once Home Assistant has created it, the existing diagnostic status entity carries the three plain-language data/authentication states and last-successful-update timestamp, subject to normal entity permissions; before then, the native integration lifecycle is authoritative. |
| C13 | 2026-08-16 | What accessibility behaviour applies to the external authorization action? | The standard Home Assistant Markdown link is keyboard-accessible, descriptively named as opening Yorkshire Water sign-in in a new tab, and precedes the callback field and submit action in logical document order; its URL is also selectable text for manual copy. |
| C14 | 2026-08-16 | May callback and provider failures share one generic error? | No. Correctable input, expired/mismatched attempts, provider denial/cancellation, and temporary unavailability use separate actionable message families. |
| C15 | 2026-08-16 | Should the sign-in-link experience add a custom frontend clipboard or focus control? | No. Keep the backend-only native Home Assistant config-flow architecture; use an external Markdown link and selectable URL text for manual copy with standard Home Assistant keyboard behaviour. |
| C16 | 2026-08-16 | Should the integration card carry custom persistent authentication and staleness labels? | No. Use Home Assistant's native Loaded, Setup retry/retry reason, and Needs attention/reauthentication lifecycle; once created, the existing diagnostic status entity carries the exact three plain-language states and last-successful-update timestamp. |

## 8. Design Review

<!-- Filled by /look-and-feel. Empty design review = gate stays red for UI-facing features. -->

- **Overall impression:** Design-ready at specification level. The revised status boundary now fits native Home Assistant behaviour: the integration entry communicates lifecycle and exposes the native reauthentication action, while the existing diagnostic status entity carries the exact non-secret data/authentication state and last-successful-update detail after entity setup. This avoids implying that a backend integration can add bespoke labels or actions to the integration card. No active design lens was applied because the project has no constitution.
- **Heuristics findings:** No open findings.
  - **Resolved — Native authorization action:** AC-2.2, C9, C15, and the explicit out-of-scope item require a non-editable, descriptively named external Markdown link, the same destination as selectable URL text, and explicit return instructions. This preserves recognition and error prevention within native Home Assistant constraints without reintroducing the existing editable `authorization_url` field or requiring a custom clipboard control.
  - **Resolved — Recovery and restart:** AC-2.8, AC-2.9, AC-4.4, AC-4.5, C10, and NFR-9 distinguish correctable input from abandoned, expired, mismatched, denied, and cancelled attempts; they provide a visible fresh-start path and invalidate old state, resolving the prior user-control and error-recovery finding.
  - **Resolved — Primary and fallback hierarchy:** AC-4.2, AC-5.2, AC-6.1, AC-6.4, and C11 make guided sign-in primary, place temporary access-token entry behind an advanced secondary choice, and exclude implementation terminology from the customer journey, resolving the prior hierarchy and consistency finding.
  - **Resolved — Native lifecycle and diagnostic status:** AC-4.1, AC-4.4, AC-4.6, AC-4.7, C12, C16, NFR-7, and the explicit out-of-scope item consistently separate the two native surfaces. The integration entry shows Home Assistant's applicable Loaded, Setup retry, or Needs attention lifecycle and native action; once created, the diagnostic status entity shows exactly one plain-language current/delayed/sign-in state plus `last_successful_update`. The pre-platform-setup case is explicitly covered, resolving the prior visibility-of-status finding without requiring a custom card.
  - **Resolved — Permissions boundary:** AC-2.6 limits configuration and reauthentication to administrators through native Home Assistant permissions while allowing the non-secret diagnostic entity to follow normal entity permissions. This is consistent with the target administrator journey and does not expose an authorization action or secret state to non-administrators.
  - **Resolved — Actionable message families:** AC-2.4, AC-2.5, AC-2.8, AC-2.9, C14, and NFR-7 separate correctable callback input, temporary provider failure, invalid attempts, and denial/cancellation into distinct safe next actions, resolving the prior generic-error finding.
- **Accessibility notes:** No open findings. The lifecycle presentation and reauthentication action inherit native Home Assistant keyboard, focus, naming, and contrast behaviour. The diagnostic status entity communicates each state in text rather than colour and supplies the update time as text data, so the essential status is available to assistive technology wherever normal entity permissions grant access. AC-2.7, C13, and NFR-4 continue to cover the native sign-in form. `/demo-day` must verify the rendered lifecycle/action, diagnostic entity state and timestamp, non-admin view, Markdown-link keyboard behaviour, focus order, labels, and error handling in the supported Home Assistant frontend.
- **Design risks & required changes:** None at specification level. The revised lifecycle/entity split is internally consistent, preserves status visibility before and after platform setup, and stays within native permissions and accessibility behaviour. The previous five Major findings and one Minor finding remain resolved. No screenshots are required for this Mode A review; rendered native Home Assistant evidence remains required at `/demo-day`. The Designer has not changed approval status or SPEC GATE boxes.

---

## ✅ SPEC GATE

*All boxes checked → `/sprint-plan` may start. Any box open → back to `/story-time` or `/look-and-feel`.*

- [x] Problem, goal and success signal are concrete (no buzzwords, no "everyone")
- [x] Every story has testable Given/When/Then acceptance criteria
- [x] Stories are prioritized (MoSCoW) and at least one is a Must
- [x] Non-functional requirements are stated and measurable (or marked N/A with reason)
- [x] Clarify pass done: no ambiguity left unresolved or unparked
- [x] Open questions are resolved or explicitly accepted as risk
- [x] Out-of-scope section is filled (something was consciously cut)
- [x] Constitution (`.spark/constitution.md`) respected, or conflicts recorded as open questions
- [x] Design review done for UI-facing features (or marked N/A with reason)
- [x] Status set to `approved` by the user
