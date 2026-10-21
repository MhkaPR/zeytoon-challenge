# Feature Specification: SMS OTP Login (User Frontend & Backend)

**Feature Branch**: `001-sms-otp-login`

**Created**: 2026-10-21

**Status**: Draft

**Input**: User description: "Implementation of only and only 'login' on all three sides (user frontend, admin frontend, backend). Nothing else should be implemented: no separate registration, no account recovery, no profile, no provider panel, no regular-user capabilities. Scope: only the login flow with phone number and SMS OTP; three sides; roles guest, regular user, admin; guest can only search, filter, compare (outside scope, only guest state must be identifiable); provider panel out of scope. Login flow: enter phone, request OTP, receive by SMS, enter OTP, on success issue session/token; phone is unique identifier, existing phone logs in, new phone creates the user (implicit signup inside login); after login return to the same page (return URL), invalid return URL goes to default page; admin frontend uses the same OTP flow but only admin-role users may enter the admin panel; no other profile info collected. OTP rules: stored in backend with Redis and TTL; expiration countdown shown in frontend; expired code message is only 'The code is incorrect' and must not say it expired; failed-attempt limit and post-threshold behavior must be specified. Edge cases: invalid phone, high request rate, wrong OTP, expired OTP, blocked user (message 'To resolve the block, contact us through the following communication channels' plus the channels), invalid return URL, non-admin attempting admin login, no account deletion and no account merging. Security: strong hashing for stored sensitive data; CORS exact allowlist for both frontends; CSRF protection with specified strategy; JWT with specified expiration, refresh, and revocation policy; rate limiting on OTP request and verification endpoints, attempt-count limits, temporary lockout, and overall request limiting; masking the phone number in all logs is mandatory."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Regular user logs in with phone + SMS OTP (Priority: P1)

A visitor on the user-facing site enters their phone number, requests a one-time code, receives it by SMS, and enters it. On success the system logs them in, creating the account implicitly if the phone number is new, and returns them to the page they were on before logging in.

**Why this priority**: This is the only path by which a regular user gains an authenticated session, and it is the core deliverable of the feature. Without it, nothing else in the login scope has value.

**Independent Test**: From a logged-out state, enter a valid phone number, request a code, enter the correct code, and confirm the user lands authenticated on the originally requested page. A brand-new phone number must result in a usable account with no separate registration step.

**Acceptance Scenarios**:

1. **Given** a guest on a page that requires login, **When** they enter a valid phone number and request a code, **Then** a code is sent by SMS and a countdown to expiry is shown.
2. **Given** a code has been requested and not expired, **When** the user enters the correct code, **Then** they are logged in and returned to the page they were on before login.
3. **Given** a phone number that has never been used before, **When** the user completes verification with the correct code, **Then** an account is created for that phone number and the user is logged in (no separate registration step).
4. **Given** a phone number that already belongs to a user, **When** the user completes verification with the correct code, **Then** the existing user is logged in (no duplicate account is created).
5. **Given** a login was initiated from a specific page, **When** login succeeds, **Then** the user is returned to that page.

---

### User Story 2 - Guest state is identifiable and login is offered without blocking browsing (Priority: P2)

An unauthenticated visitor can browse, search, filter, and compare. The system can always tell that they are a guest, and when they attempt an action that requires an identity they are prompted to log in and, after logging in, returned to where they were.

**Why this priority**: The feature must not break the public browsing experience, and downstream features need a reliable guest-vs-authenticated signal. It is lower priority because it is a boundary condition of the login flow rather than the login flow itself.

**Independent Test**: Visit a public page while logged out, confirm browsing works and the session is treated as guest, then trigger a login-required action and confirm the login prompt and post-login return.

**Acceptance Scenarios**:

1. **Given** no valid session, **When** any page is loaded, **Then** the request is treated as a guest request.
2. **Given** a guest, **When** they use public search, filter, and compare features, **Then** no login is required (these features themselves are outside this feature's scope).
3. **Given** a guest, **When** they attempt an action that requires an identity, **Then** they are prompted to log in and, after success, returned to the originating page.

---

### Edge Cases

- **Invalid phone number**: rejected at request time with a validation message; no SMS is sent and no code is created.
- **High request rate (same phone)**: additional OTP requests within the cooldown are rejected with a "please wait before requesting again" message; a per-phone hourly cap applies.
- **High request rate (same source)**: requests exceeding the per-source limit are throttled/rejected to prevent abuse and DoS.
- **Wrong OTP**: rejected with the message "The code is incorrect"; the failed-attempt counter for that code increases.
- **Expired OTP**: rejected with the message "The code is incorrect" only — the system MUST NOT reveal that the code expired.
- **Failed-attempt threshold crossed**: the active code is invalidated, further verification for that code is refused, and a temporary lockout applies (see FR-016/FR-017).
- **Blocked user**: login is refused with the message "To resolve the block, contact us through the following communication channels" followed by the configured contact channels.
- **Invalid return URL**: login still succeeds, but the user is sent to the default page instead of the invalid target.
- **No account deletion, no account merging**: there is no flow to delete an account, and no flow to merge two accounts even when the same person uses two phone numbers.
- **Missing/unreachable SMS delivery**: the request is reported as sent to the user only when a code was actually created and dispatched; delivery failures are surfaced as an error without exposing internal details.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow a visitor to request a one-time code by entering a phone number.
- **FR-002**: The system MUST deliver the one-time code to the phone number by SMS.
- **FR-003**: The system MUST allow the visitor to submit the received code to complete login.
- **FR-004**: On successful verification, the system MUST issue an authenticated session/token and log the user in.
- **FR-005**: The phone number MUST be the user's unique identifier; a request for an existing phone number logs in the existing user and a request for a new phone number creates a new user implicitly within the login flow.
- **FR-006**: The system MUST NOT provide a separate registration flow, account-recovery flow, profile flow, provider panel, or any regular-user capability beyond login and the guest browsing boundary.
- **FR-007**: The system MUST NOT collect profile information during login; such information is completed later elsewhere (out of scope here).
- **FR-008**: The phone + OTP login MUST be available on the user frontend and through the backend that serves it.
- **FR-009**: The system MUST recognize three roles: guest (no valid session), regular user, and admin. The admin role exists in the data model and is enforced by the separate admin panel; this feature does not implement admin-panel access.
- **FR-010**: The system MUST allow a guest to be identified as such so public browsing continues without login (search/filter/compare themselves are out of scope).
- **FR-011**: On successful login, the system MUST return the user to the page they were on before login; if the requested return target is not a valid allowed target, the system MUST send the user to the default page.
- **FR-012**: The admin panel MUST NOT be delivered by this feature; it is a separate, restricted-domain panel with its own access rules, and this login feature MUST NOT assume or implement admin-panel access.
- **FR-013**: This feature MUST NOT integrate with, fetch data from, or surface any provider-supplied admin panel or provider administration UI.
- **FR-014**: The one-time code MUST be stored server-side with a time-to-live (TTL), and the user frontend MUST display a countdown of the remaining validity.
- **FR-015**: An expired code MUST be rejected with the message "The code is incorrect" only; the system MUST NOT state or imply that the code expired.
- **FR-016**: The system MUST enforce a maximum number of failed verification attempts per code (default: 5); on reaching the threshold the code MUST be invalidated and further attempts with it MUST be refused.
- **FR-017**: The system MUST apply a temporary lockout for the phone number after repeated failed verifications (default: lockout after 5 failed attempts for 15 minutes); during lockout, new code requests and verifications for that phone MUST be refused with a clear "try again later" message.
- **FR-018**: The system MUST reject invalid phone numbers at request time with a validation message, without sending an SMS or creating a code.
- **FR-019**: The system MUST rate-limit OTP requests per phone (default: at most 1 per 60 seconds and at most 5 per hour) and per source, and MUST apply an overall request limit to protect against DoS.
- **FR-020**: The system MUST rate-limit OTP verification attempts (default: at most 10 attempts per phone per 10 minutes) in addition to the per-code attempt limit.
- **FR-021**: A blocked user MUST be refused login with the message "To resolve the block, contact us through the following communication channels" followed by the configured contact channels.
- **FR-022**: Sensitive stored data MUST be protected with strong one-way hashing (one-time codes MUST NOT be stored in plaintext; if phone numbers are stored, they MUST be handled per the security principle).
- **FR-023**: CORS MUST be enforced with an exact allowlist covering both frontends; no wildcard origins are permitted.
- **FR-024**: CSRF protection MUST be applied to all state-changing requests, using a specified strategy: tokens are carried in `httpOnly`/`Secure` cookies and every state-changing request MUST present a matching CSRF token (double-submit).
- **FR-025**: The session/access token MUST be a JWT with a specified access expiration (default: 15 minutes) and a refresh policy (default: refresh valid 7 days, rotated on each refresh), plus a revocation mechanism (default: server-side denylist so a token can be revoked before expiry, including on logout and on admin block).
- **FR-026**: The system MUST mask phone numbers in all logs and MUST NOT log full phone numbers, full one-time codes, or tokens.
- **FR-027**: The system MUST record authentication-related security events (OTP requested, verification succeeded/failed, lockout triggered, block refusal) with masked identifiers.
- **FR-028**: There MUST be no account deletion flow and no account merging flow.
- **FR-029**: The system MUST log the user out and invalidate their tokens on request.

### Key Entities *(include if feature involves data)*

- **User**: A person identified by phone number; holds a role (regular user or admin) and a status (active or blocked). Created implicitly on first successful login. No profile attributes are collected at login.
- **One-Time Code (OTP challenge)**: A short-lived credential bound to a phone number; stores a hashed code, an expiry, a failed-attempt counter, and issuance metadata. Stored server-side with a TTL.
- **Session / Token**: The authenticated credential issued after successful verification; has an access component with an expiration, a refresh component, and a revocable state.
- **Login Attempt / Lockout state**: Records failed verification attempts and temporary lockouts per phone and per source, used to enforce thresholds.
- **Return Target**: The page the user was on before login, validated against an allowlist before use; falls back to a default page.
- **Contact Channels**: The admin-configurable list of communication channels shown to a blocked user.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time user can go from entering a phone number to being logged in within 90 seconds, assuming the SMS arrives promptly.
- **SC-002**: 95% of users who receive a code and enter it correctly are logged in on the first attempt.
- **SC-003**: 100% of login attempts from a blocked user display the block message with at least one contact channel.
- **SC-004**: 100% of attempts to enter the admin panel by a non-admin account are denied, with no admin session issued.
- **SC-005**: After login, 100% of users with a valid return target land on the page they started from; 100% of invalid targets fall back to the default page.
- **SC-006**: No log entry contains a full phone number, a full one-time code, or a token, verified across the authentication flows.
- **SC-007**: An expired code never produces any message other than "The code is incorrect".
- **SC-008**: Under a burst of repeated OTP requests from one phone or one source, the system keeps responding within normal latency and rejects excess requests rather than failing, sustaining at least 100 requests per second at peak.
- **SC-009**: Reaching the failed-attempt threshold reliably invalidates the code and triggers lockout in 100% of tested cases.

## Assumptions

- Defaults chosen where the description did not fix a value: OTP length 6 digits; OTP TTL 2 minutes; max failed attempts per code 5; temporary lockout 15 minutes after 5 failed attempts; OTP request limit 1 per 60 seconds and 5 per hour per phone; verification limit 10 per 10 minutes per phone; JWT access expiry 15 minutes; refresh validity 7 days with rotation; token revocation via server-side denylist.
- SMS delivery is provided by an external SMS gateway; choosing and configuring the gateway is an implementation concern, not part of this specification's user-visible behavior. Local environment variable handling of credentials follows the project constitution.
- Roles are assigned outside the login flow (there is no in-product role management in this feature); admin accounts are provisioned by operators.
- "Blocked" is an account state set by an operator; enforcement applies both to requesting a code and to verifying it.
- The set of valid return targets is limited to the known frontend origins/paths; anything else is treated as invalid and replaced with the default page.
- Contact channels shown to blocked users are configurable by operators.
- The phone number format and validity rules follow the target market's national numbering plan; invalid inputs are rejected before any SMS is sent.
- Public browsing (search, filter, compare) already exists or is delivered by other features; this feature only guarantees that the guest state is identifiable and that login can be triggered from it.
- Caching, queues, the local search index, and containerized hosting are provided by the platform per the project constitution and are not re-specified here.
