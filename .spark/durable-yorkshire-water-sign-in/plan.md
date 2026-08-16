# Plan: durable-yorkshire-water-sign-in

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/durable-yorkshire-water-sign-in/spec.md` (must be `approved`) |
| **Status** | `approved` |
| **Date** | 2026-08-16 |

<!-- Budget: ~300 lines. The plan is /increment's backlog and the Reviewer's yardstick — both read it
     in full, repeatedly, and a fix round reads it again. Argue the architecture in §1 tightly; the
     task table earns the space, the prose around it usually doesn't. A plan that needs far more than
     this is describing an increment too large to review in one pass — cut scope, don't cut detail. -->

## 1. Architecture Decision

<!-- Mini-ADR. The EM decides — but shows the alternatives that were rejected and why. -->

- **Context:** The integration is a dependency-free, backend-only Home Assistant custom component. It already has experimental OAuth 2.0 Authorization Code + PKCE helpers, token exchange/refresh code, a config/reauth flow, coordinator-driven polling, a diagnostic status sensor, and lightweight tests that stub Home Assistant. The supported journey must stop exposing raw codes/verifiers/token JSON, retain the existing config entry, and enable persistent authorization only after redacted live evidence proves both refresh-token issuance and renewal. Native Home Assistant—not integration code—owns config-entry lifecycle wording, administrator access, link rendering, keyboard behaviour, and reauthentication presentation.
- **Decision:** Keep the current modules and native config-flow architecture. Introduce an in-memory, expiring PKCE attempt owned by each flow; accept only a complete callback URL whose redirect target and state match that attempt; render the generated destination as a translated external Markdown link plus selectable text; and use native reauth/config-entry lifecycle APIs. Gate `offline_access` and refresh-token claims behind an explicit code-level capability switch tied to a secret-free evidence record; when enabled, rotate token data atomically in the existing config entry. Keep the existing diagnostic status entity available across post-setup failures and derive its three specified states from coordinator/auth state.
- **Alternatives considered:**

  | Alternative | Why rejected |
  |---|---|
  | Home Assistant application-credentials OAuth helper | Yorkshire Water is not a registered Home Assistant OAuth provider and the captured portal uses a fixed first-party client/redirect URI; adopting the helper would imply a provider contract and callback ownership not yet evidenced. |
  | Custom frontend/panel with clipboard and status controls | Explicitly out of scope in C15/C16, adds JavaScript packaging and a second UI lifecycle, and duplicates native accessibility and integration lifecycle behaviour. |
  | Persist PKCE verifier/state in the config entry so abandoned flows can resume | Violates NFR-9, lengthens the lifetime of sensitive attempt material, and permits stale attempts to outlive the flow that created them. |
  | Continue the existing options-first experimental OAuth and DevTools inputs | Exposes implementation terminology and secret-entry fields, does not make guided sign-in primary, and cannot satisfy recovery/error-family requirements. |
- **Consequences:** The change stays within established files, adds no package or service, and old bearer-token entries remain valid until reauth. Flow cancellation naturally discards attempt secrets, and a replacement attempt invalidates prior state. Native UI behaviour must be verified in a supported Home Assistant host because stubs cannot prove Markdown rendering, permissions, focus, or lifecycle presentation. Persistent renewal remains shipped-but-disabled unless the evidence gate is approved; maintaining the capability later requires updating both the secret-free evidence record and the guarded constant.

## 2. Affected Components

<!-- Files, modules, services, external dependencies. New dependencies need a justification. -->

- `custom_components/yorkshire_water/config_flow.py`: native setup/reauth menus, guided attempt lifecycle, strict callback handling, restart, migration-safe entry update, and advanced fallback.
- `custom_components/yorkshire_water/api.py`: callback parser, provider error taxonomy, timeout handling, capability-safe token exchange/refresh, and replacement-token rotation.
- `custom_components/yorkshire_water/const.py`: attempt lifetime, plain-language status values, and evidence-gated persistent-authorization settings.
- `custom_components/yorkshire_water/__init__.py`: coordinator retry/auth classification, one-incident reauth, atomic auth persistence, native initial setup retry, and runtime status data.
- `custom_components/yorkshire_water/sensor.py`: diagnostic status availability/value/attributes while ordinary data entities are delayed or awaiting sign-in.
- `custom_components/yorkshire_water/strings.json` and `custom_components/yorkshire_water/translations/en.json`: native labels, Markdown destination/selectable URL, instructions, advanced fallback, and distinct safe errors.
- `tests/smoke_response_shapes.py`: existing dependency-free auth/API/integration stubs extended for the full Must-story path and Should-story compatibility.
- `docs/auth_capability_evidence.md`: secret-free capability decision record and approval checklist; no raw capture is retained.
- `README.md`, `docs/token_retrieval.md`, and `docs/redaction_checklist.md`: supported journey, fallback/migration, evidence procedure, and removal of DevTools from the primary instructions.
- External systems: Yorkshire Water authorize/token endpoints and the native Home Assistant config-flow, config-entry, coordinator, and sensor APIs. No new runtime or test dependency is introduced; rendered-host checks remain part of `/demo-day`.
- No aSPARK graph runner or graph was available, so affected components were scoped by direct repository inspection.

## 3. Task Breakdown

<!-- Ordered. Every task maps to the spec by ID (the story and the specific AC-n.m / NFR-n it serves)
     and has its own definition of done. The "Covers" column is the traceability spine: every Must AC
     and every applicable NFR must appear against at least one task.
     /increment works through this table top to bottom — nothing else — and keeps Status current.

     End each Definition of Done with a `files:` note naming the files the task is expected to
     touch, so the task→code link is declared instead of guessed by whoever reads the plan later:

         … and a test proves it — files: src/auth/session.ts, src/auth/session.test.ts

     Four rules:
     1. Repo-relative POSIX paths, comma-separated.
     2. The note is the **last** thing in the cell — nothing after the paths.
     3. **No** trailing punctuation after the last path.
     4. If the touched files are not knowable at plan time, **omit** the note —
        never guess. -->

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Lock the persistent-authorization evidence gate and define auth attempt/error primitives | US-1, US-2 | AC-1.1, AC-1.2, AC-1.3, AC-2.4, AC-2.5, AC-2.8, AC-2.9, NFR-2, NFR-3, NFR-9 | – | `done` | A default-off capability function cannot request or claim persistent access without a non-empty approved evidence ID; a secret-free record captures requested/issued/expired-renewal outcomes; strict callback parsing rejects missing, wrong-origin, expired, replay/mismatch, denial, and cancellation cases as distinct safe error types; tests prove no secret is included in their string forms — files: custom_components/yorkshire_water/const.py, custom_components/yorkshire_water/api.py, docs/auth_capability_evidence.md, tests/smoke_response_shapes.py |
| T2 | Build the guided setup walking skeleton from native start page to connected entry | US-1, US-2 | AC-1.1, AC-1.3, AC-2.1, AC-2.2, AC-2.3, AC-2.4, AC-2.5, AC-2.6, AC-2.7, AC-2.9, NFR-1, NFR-2, NFR-3, NFR-4, NFR-7, NFR-9 | T1 | `done` | The primary native flow creates a time-limited PKCE attempt, shows no password/token/code/verifier fields, renders the named Markdown link before one labelled callback field with the same URL as selectable text, exchanges a valid matching callback, creates the entry, and maps input/denial/provider-timeout failures to distinct translated recoverable forms; stub integration tests cover the end-to-end path and verify the schema/placeholder order and absence of secret fields — files: custom_components/yorkshire_water/config_flow.py, custom_components/yorkshire_water/strings.json, custom_components/yorkshire_water/translations/en.json, tests/smoke_response_shapes.py |
| T3 | Add safe Start again and one-attempt lifecycle semantics | US-2, US-4 | AC-2.4, AC-2.8, AC-2.9, AC-4.5, NFR-2, NFR-3, NFR-9 | T2 | `done` | The callback form exposes a standard labelled Start again control after invalid/expired/mismatched/denied/cancelled outcomes; invoking it replaces verifier, state, URL, and expiry before rendering the new attempt; tests prove the old callback cannot update an entry and completed/restarted flow results contain no attempt secret — files: custom_components/yorkshire_water/config_flow.py, custom_components/yorkshire_water/strings.json, custom_components/yorkshire_water/translations/en.json, tests/smoke_response_shapes.py |
| T4 | Make guided reauthentication primary and preserve the existing entry | US-4, US-5 | AC-4.1, AC-4.2, AC-4.3, AC-4.4, AC-4.5, AC-5.1, AC-5.2, AC-5.3, NFR-3, NFR-6, NFR-9 | T3 | `done` | Reauth uses the same guided steps, resolves the linked entry with native helpers, updates/reloads that entry without creating another, preserves account/meter data and unique ID, and leaves cancellation/failure retryable; tests prove repeated auth failures start one flow and successful migration retains entry/entity/statistics identity inputs — files: custom_components/yorkshire_water/config_flow.py, custom_components/yorkshire_water/__init__.py, custom_components/yorkshire_water/strings.json, custom_components/yorkshire_water/translations/en.json, tests/smoke_response_shapes.py |
| T5 | Harden refresh rotation and temporary-versus-terminal provider failures | US-3, US-4 | AC-3.1, AC-3.2, AC-3.3, AC-3.4, AC-4.1, NFR-1, NFR-2, NFR-5, NFR-6 | T1 | `done` | Refresh runs only when capability evidence is enabled and a refresh token exists; successful responses atomically retain a prior refresh token when omitted or replace it when supplied; invalid/revoked authorization requests reauth, while network/5xx/over-30-second failures remain retryable; time-controlled tests simulate more than 30 days, multiple expiries, rotation, a transient failure, and recovery without duplicate entities or user input — files: custom_components/yorkshire_water/api.py, custom_components/yorkshire_water/__init__.py, tests/smoke_response_shapes.py |
| T6 | Align native config-entry lifecycle and coordinator recovery | US-3, US-4 | AC-3.4, AC-4.1, AC-4.3, AC-4.4, AC-4.7, NFR-1, NFR-6, NFR-7 | T4, T5 | `done` | Initial temporary failure enters native Setup retry with a secret-free reason; invalid/revoked auth enters native Needs attention with one reauth flow; later temporary failures retain last successful coordinator data and retry normally; success reloads the same entry and returns it to Loaded; integration-stub tests prove each exception path and deduplication — files: custom_components/yorkshire_water/__init__.py, tests/smoke_response_shapes.py |
| T7 | Implement the diagnostic status state machine without hiding stale data | US-4 | AC-4.1, AC-4.4, AC-4.6, AC-4.7, NFR-2, NFR-6, NFR-7 | T6 | `done` | Once created, the existing status entity remains available during delayed/sign-in states, exposes exactly the specified current/delayed/sign-in text and latest non-secret `last_successful_update`, while ordinary sensors follow coordinator availability; unit/stub tests cover success, post-success retry, sign-in required, and no-prior-success cases — files: custom_components/yorkshire_water/__init__.py, custom_components/yorkshire_water/sensor.py, tests/smoke_response_shapes.py |
| T8 | Retain the advanced temporary-token migration escape hatch | US-5, US-6 | AC-5.1, AC-5.2, AC-5.3, AC-6.1, AC-6.2, AC-6.3, AC-6.4, NFR-2, NFR-7 | T4 | `done` | Existing valid bearer entries load unchanged; setup/reauth places "Use a temporary access token (advanced)" behind the guided route; a valid token updates the same entry only for its lifetime; expiry returns to guided reauth; primary forms and messages contain none of the prohibited implementation terms; tests prove hierarchy, preservation, and expiry behaviour — files: custom_components/yorkshire_water/config_flow.py, custom_components/yorkshire_water/__init__.py, custom_components/yorkshire_water/strings.json, custom_components/yorkshire_water/translations/en.json, tests/smoke_response_shapes.py |
| T9 | Complete security regression coverage and supported-user documentation | US-1, US-2, US-3, US-4, US-5, US-6 | AC-1.2, AC-2.1, AC-2.2, AC-2.3, AC-2.5, AC-2.6, AC-2.7, AC-3.3, AC-4.3, AC-4.6, AC-4.7, AC-5.3, AC-6.4, NFR-1, NFR-2, NFR-3, NFR-4, NFR-5, NFR-6, NFR-7, NFR-8, NFR-9 | T1–T8 | `done` | Redaction tests scan nested logs/errors/forms/status/evidence for every secret class; documentation makes guided sign-in primary, labels evidence-gated durability and advanced fallback accurately, and removes DevTools extraction from the supported journey; `python -m compileall custom_components/yorkshire_water`, `python tests/smoke_response_shapes.py`, and `python -m unittest tests/test_statistics_import.py` all pass — files: README.md, docs/token_retrieval.md, docs/redaction_checklist.md, tests/smoke_response_shapes.py |

## 4. Test Strategy

<!-- What gets unit tests, what gets integration tests, what is left to /demo-day in the browser. -->

- **US-1 — evidence gate:** Unit/stub tests keep persistent scope and claims off with no evidence ID, permit the refresh path only with the controlled capability fixture, and scan the evidence record and errors for secret material. `/peer-review` verifies the record cannot be mistaken for live proof. Live approval of redacted provider evidence remains a release gate, not an automated assertion.
- **US-2 — guided sign-in:** Dependency-free config-flow stubs exercise initial page, link generation, strict callback parsing/exchange, correctable malformed input, timeout/unavailability, denial/cancellation, mismatch/expiry, and restart. `/demo-day` in supported Home Assistant verifies admin-only initiation, Markdown new-tab rendering, selectable URL, keyboard order/labels/error focus, under-two-second local forms, and the real portal callback journey; browser rendering and native permissions cannot be proven by repository stubs.
- **US-3 — unattended renewal:** API/coordinator tests use a controllable clock and sequenced token responses to cross 30 simulated days, expire multiple access tokens, rotate replacement authorization, preserve a refresh token when omitted, survive a temporary failure, and persist each successful rotation. `/demo-day` combines these fixtures with the approved redacted live evidence gate; an actual 30-day live run is release evidence when provider support is enabled.
- **US-4 — guided recovery:** Integration/config-flow stubs cover unavailable versus rejected/revoked auth, one reauth incident, native linked-entry update/reload, restart invalidation, unchanged identifiers, cancellation, diagnostic states, and last-update preservation. `/demo-day` verifies native Loaded/Setup retry/Needs attention presentation, native action, existing entity/statistics continuity, stale status visibility, and recovery without deleting the entry.
- **Regression/Should stories:** Existing response-shape and statistics-import suites remain green. Stub tests cover non-forced bearer migration and the advanced fallback hierarchy/lifetime. `/peer-review` inspects all logs, diagnostics, form results, exceptions, and entry updates for secret leakage and confirms removal cleans up retained authorization through normal config-entry deletion.

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Yorkshire Water does not issue a refresh token or rejects `offline_access` | The 30-day unattended path cannot be enabled | Ship the guided recovery path with the capability default off; enable persistent claims only after the approved secret-free evidence record proves issuance and post-expiry renewal. |
| The portal callback shape, denial parameters, or redirect target changes | Valid users may see an invalid-attempt error or exchange may fail | Centralize strict parsing and provider error mapping, cover captured redacted shapes with fixtures, fail closed without logging query values, and keep Start again available. |
| Flow-local state is lost on Home Assistant restart | An in-progress sign-in cannot resume | Treat it as an expired attempt and offer Start again; do not persist verifier/code/state merely to resume a short human interaction. |
| Native Markdown or lifecycle presentation differs across supported Home Assistant versions | Labels, new-tab behaviour, focus, or status presentation may miss UI ACs | Use only documented native primitives, avoid custom UI, and gate release on `/demo-day` in the declared supported version; record the tested Home Assistant version. |
| Reauth deduplication races with repeated coordinator failures | Multiple flows or reloads could appear | Keep one incident flag per loaded entry, use `entry.async_start_reauth(hass)`, test concurrent/repeated failures, and clear state only after successful reload or a new incident. |
| Refresh succeeds remotely but config-entry persistence/reload fails | In-memory and stored authorization can diverge | Build the full replacement payload first, update the existing entry once, retain the latest valid in-memory credentials for the current request, and retry/prompt safely without exposing tokens. |
| Keeping the status sensor available during coordinator failure masks availability semantics | Users may mistake stale usage entities for current data | Special-case only the diagnostic status entity, preserve the timestamp, use the exact delayed/sign-in text, and leave ordinary entities governed by coordinator availability. |
| Lightweight stubs drift from real Home Assistant APIs | Repository tests pass while host flow fails | Keep calls aligned with official native helpers and make rendered config-flow, non-admin, lifecycle, reauth, reload, and removal checks mandatory at `/demo-day`. |

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft)
- [x] Architecture decision includes rejected alternatives (a decision without alternatives is a guess)
- [x] Architecture respects the constitution's technical constraints (or a conflict is recorded)
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies
- [x] Test strategy covers every Must story
- [x] Status set to `approved` by the user
