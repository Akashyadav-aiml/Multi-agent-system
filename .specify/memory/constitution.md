<!--
Sync Impact Report
==================
Version change: 1.0.0 → 1.1.0
Bump rationale: MINOR — new principle "VII. Design Tokens & Visual Hierarchy"
added. No existing principle removed or redefined; previously-implicit
"Three colors only" design-system rule formalized into the constitution and
expanded to permit a text-hierarchy ramp + dark-surface ramp + single accent.

Modified principles:
  - none redefined

Added principles:
  - VII. Design Tokens & Visual Hierarchy (governs portal UI text/color/weight)

Modified sections:
  - Governance § footer: version + Last Amended date bumped

Templates requiring updates:
  - ✅ no change required: .specify/templates/plan-template.md
  - ✅ no change required: .specify/templates/tasks-template.md
  - ✅ no change required: .specify/templates/spec-template.md
  - ✅ no change required: .specify/templates/checklist-template.md
  - ✅ no change required: CLAUDE.md

Companion document updates (must land in same PR):
  - design-system/whatsapp-operations-portal/MASTER.md — "Palette Rules" +
    "Typography" sections rewritten to enumerate the new tokens.

Rationale for expanding the palette:
  - Single-accent + greyscale-text rule from MASTER.md left "muted text"
    indistinguishable from "secondary text"; in practice `text-brand-500`
    was used as both an accent AND a subtitle dim, producing low-contrast
    subtitles rendered in gold.
  - WCAG AA (4.5:1 body / 3:1 large) requires explicit contrast levels;
    single-text-color + opacity dimming failed in inputs (white-on-white
    on the /login screen) and in dim metadata throughout.
  - Dark-mode optical thinning needs heavier UI text weight than light
    mode; weight ceiling remains 600 — hierarchy carried by SIZE + COLOR.

Deferred TODOs: none
-->

# WhatsApp Demo Portal Constitution

The WhatsApp Demo Portal links a WhatsApp account via Baileys to an operator-facing
web portal for monitored, manual messaging. The portal is moving from local-only
demo to a production-ready internal tool. This constitution sets the
non-negotiable rules that govern that transition.

## Core Principles

### I. Security-First Authentication (NON-NEGOTIABLE)

Every portal route except `/login` and `/api/auth/*` MUST require an
authenticated session. Authentication MUST satisfy:

- Passwords stored with bcrypt at cost factor ≥ 12, with a server-side pepper
  loaded from environment.
- Session tokens MUST be JWTs delivered via `httpOnly`, `Secure`,
  `SameSite=Strict` cookies. Tokens MUST NOT appear in URLs, logs, or
  client-readable storage.
- All state-changing requests (POST/PUT/PATCH/DELETE) MUST present a CSRF
  token validated server-side.
- `/api/auth/login` MUST be rate-limited to 5 attempts/minute/IP.
- An account MUST lock for 15 minutes after 10 failed login attempts.

Rationale: The portal controls a live WhatsApp account. Account takeover lets
an attacker impersonate the account holder. Network-edge defenses are not
present in the demo, so auth MUST be correct at the application layer.

### II. RBAC With Least Privilege

The portal MUST enforce three roles, checked server-side on every endpoint:

- `admin`: full access, including user management and `/api/logout` (WhatsApp
  unlink).
- `operator`: read chats, send messages, fetch history, mark read.
- `viewer`: read-only — no send, no history fetch, no WA logout.

Role checks MUST happen at the route handler, not only in the UI. Permission
denials MUST emit an audit-log event and return `403`.

Rationale: A read-only auditor needs different access than a messaging
operator. Hiding buttons in the UI is not a security boundary; the server is.

### III. Test-First (NON-NEGOTIABLE)

Auth, RBAC, and audit-logging behaviour MUST have contract tests and
integration tests written, executed, and observed to FAIL before any
implementation is merged. Mandatory coverage:

- Login success and failure paths.
- Lockout after threshold.
- CSRF token rejection.
- Role-based denial for each role/endpoint pair.
- Session expiry and refresh.

Rationale: Auth bugs are silent failures. A passing implementation written
before a failing test proves nothing; we need the red-green-refactor cycle.

### IV. Observability Without Leakage

Every request MUST be logged with structured pino output and a correlation
`requestId`. Logs MUST NEVER contain: passwords, JWTs, CSRF tokens, bcrypt
hashes, message bodies, or media payloads.

Auth-relevant events — `login.success`, `login.failure`, `logout`,
`lockout`, `role.denied`, `user.created`, `user.role_changed` — MUST be
persisted to an append-only audit-log table, not only to stdout.

Rationale: Production incidents require trace correlation; compliance
review requires audit retention; PII leakage is itself an incident.

### V. No Auto-Reply

The portal MUST NOT send WhatsApp messages without an explicit, authenticated
operator action originating from a user request. No keyword rules, no LLM
auto-responders, no scheduled message engines.

Rationale: This is an internal demo with a real WhatsApp account on the
other end. Autonomous sending creates legal, compliance, and trust risk
that the system is not scoped to manage.

### VI. Secrets Hygiene

Secrets — JWT signing key, bcrypt pepper, session-cookie key, any future
API credentials — MUST be loaded from environment variables only. They MUST
NOT be committed to the repository. `.env.example` MUST enumerate every
required key with a placeholder.

The backend MUST refuse to boot in production (`NODE_ENV=production`) if any
required secret is missing or shorter than the minimum entropy declared in
`.env.example`.

Rationale: Committed secrets are the most common preventable breach. A boot
failure on missing secrets surfaces misconfiguration immediately rather than
producing a quietly-insecure deploy.

### VII. Design Tokens & Visual Hierarchy

Every portal UI surface MUST style text and color exclusively through the
tokens declared in `design-system/whatsapp-operations-portal/MASTER.md` and
materialized in `frontend/app/globals.css` + `frontend/tailwind.config.js`.

The token set is closed and authoritative:

- **Surface ramp**: `--bg-base`, `--bg-surface`, `--bg-elevated`.
- **Text ramp**: `--text-primary`, `--text-secondary`, `--text-tertiary`,
  `--text-disabled`.
- **Accent (single)**: `--text-accent`. Used only for CTAs, active states,
  eyebrows, key numerals, focus rings.
- **Border**: `--border-subtle`.

Rules:

- No hardcoded hex or `rgba(...)` in components, stylesheets, or inline
  `style` props. Every color MUST resolve to a token.
- No `opacity-*` utility for dimming text. Use `text-tertiary` or
  `text-disabled` instead — opacity-dimming silently fails WCAG checks and
  obscures hierarchy intent.
- Heading weight ceiling: **600**. Hierarchy is carried by **size + color**
  together, never by weight alone. h1 (largest, brightest) > body
  (mid-size, secondary) > metadata (smaller, tertiary).
- WCAG AA contrast (4.5:1 body, 3:1 large text) MUST hold for every
  text/background pairing. `text-disabled` is permitted only for inactive
  placeholders / empty-state `—` markers per WCAG 1.4.3 exemption.
- Inputs MUST set explicit `bg-*` AND `text-*` classes. Browser UA defaults
  diverge from the dark surface and produce invisible text.

Rationale: An operations portal is read more than it is clicked. Low
contrast is a correctness bug, not a polish bug: an admin who can't read
a timestamp can't audit. Pinning the palette to a typed token surface
prevents drift back into ad-hoc opacity dimming and ambiguous accent
reuse.

## Security & Compliance Constraints

- **Storage**: User accounts, sessions, audit log, and login-attempt
  counters MUST live in SQLite via `better-sqlite3` with versioned
  migrations under `backend/db/migrations/`. Existing `data.json` for chats
  remains; it is not in scope for this constitution beyond not regressing.
- **Compliance baseline**: OWASP Top 10 (2021) — every PR touching auth,
  input handling, or session management MUST be reviewed against it.
- **Transport**: When deployed beyond localhost, the portal MUST be served
  over HTTPS. Cookies MUST set `Secure`. HTTP listeners MUST redirect.
- **Dependencies**: Auth-relevant dependencies (`bcrypt`, `jose`,
  `better-sqlite3`, rate-limit middleware) MUST be pinned to a known-good
  version range and reviewed on update.

## Development Workflow & Quality Gates

- **PR gate**: Every PR MUST pass contract tests, integration tests, and
  linting. PRs that fail any of these MUST NOT be merged.
- **Constitution check**: `/speckit-plan` MUST include a Constitution Check
  section enumerating which principles apply and how the plan satisfies
  each. Violations require a Complexity Tracking entry with justification.
- **Migration discipline**: Every schema change ships as a new numbered
  migration; migrations MUST be idempotent and forward-only in production.
- **Logging discipline**: Any new request handler MUST emit at least one
  structured log line with `requestId`, route, status, and latency.
- **Review depth**: Changes to auth, RBAC, audit logging, or secret
  loading MUST be reviewed by a second person before merge.

## Governance

This constitution supersedes ad-hoc decisions and any conflicting guidance
in `README.md`, `PROJECT.md`, or skill outputs. Where another document
disagrees, this document wins until it is amended.

**Amendment procedure**: Open a PR that modifies `.specify/memory/constitution.md`
together with a Sync Impact Report at the top of the file describing the
version bump, the changed principles, and which templates were updated.

**Versioning policy**:
- MAJOR — a principle is removed or redefined in a backward-incompatible way.
- MINOR — a new principle or governance section is added, or an existing
  one is materially expanded.
- PATCH — wording, clarification, or typo fixes without semantic change.

**Compliance review**: At the end of every implemented feature, the
`/speckit-analyze` skill MUST confirm the artifacts comply with this
constitution.

**Version**: 1.1.0 | **Ratified**: 2026-05-12 | **Last Amended**: 2026-05-13
