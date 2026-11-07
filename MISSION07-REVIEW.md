# Mission 07 — product presentation and consent-first review

## Fresh authenticated baseline

On 2026-11-07, the GitHub connector independently confirmed:

- Public `AlirezaBelal/batch-sms-campaign-automation`, master
  `efa2d84b18547dbf752dd0b1458a1b56a3485604`, no open PRs; #5–#8 merged.
- Private `AlirezaBelal/alirezabelal.github.io`, master
  `d34988e327cd39d14dabc63ee619a8565567d90a`. Existing unrelated work is excluded.
- Active master rulesets, PR-only changes, zero mandatory approving reviews,
  no bypass actors. Product requires Python 3.10–3.14, coverage, dependency/data
  audit and Docker. Portfolio allows squash merges. Protections are unchanged.
- Product CI 42108345805 and Pages 42104798750 succeeded. Portfolio's Mission 06
  deployment, browser QA and Lighthouse succeeded. Product Homepage was empty.

Read actual main/config/campaign/manifest/gateway/utils, all tests, README,
SECURITY, environment example, dependencies, Docker ignore/build, CI/Pages,
static site and relevant private portfolio components/data/contracts/workflows.
Compared README claims against source. Inspected both initial public pages with
Chromium. No historical SHA was substituted for the fresh audit.

## Product and external architecture

The site now introduces installable Python software and routes Get Started to
OS-specific installation. Its first command is `python main.py`, which remains
offline Dry Run. The real path is operator-reviewed Python → authenticated HTTPS
gateway API → external Android app → SIM/carrier → recipient, if delivered.
Acceptance, queueing, processing and delivery are explicitly distinct.

The official documentation was rechecked without contacting a live gateway:

- https://docs.sms-gate.app/installation/
- https://docs.sms-gate.app/getting-started/
- https://docs.sms-gate.app/getting-started/local-server/
- https://docs.sms-gate.app/getting-started/public-cloud-server/
- https://docs.sms-gate.app/features/sending-messages/
- https://docs.sms-gate.app/integration/authentication/
- https://github.com/capcom6/android-sms-gateway

The documented cloud POST `/3rdparty/v1/messages`, `textMessage.text`,
`phoneNumbers`, TTL and Basic-auth compatibility match the existing client.
Upstream now recommends JWT for new integrations; this client remains Basic.
Local HTTP examples are not claimed directly compatible: the CLI requires HTTPS
and a trusted TLS proxy/equivalent deployment plus verified routes. Public cloud
processing and the absence of client end-to-end encryption are disclosed.
No APK, phone app, private server deployment, delivery polling or new provider
integration is supplied by this repository.

## Small confirmed engineering fixes

- `campaign.py:130,151`: callers trimmed phone fields before normalization,
  bypassing the normalizer's rejection of leading/trailing controls. Pass the
  original CSV field for both recipients and suppression entries. Regression
  tests cover quoted newline/CR/tab values and zero mocked submissions.
- `sms_service/sms_sender.py:90`: close each HTTP response in `finally`, including
  classification failures. Mocked tests verify cleanup for acknowledgements,
  rejection, server failures and exceptions. Request schema/authorization,
  pacing, classifications, no-retry behavior and journal semantics are unchanged.
- `docs/app.js:66,71`: collect denied IDs before processing rows. Any missing
  consent now denies the entire duplicate identity, independent of row order,
  as existing opt-out handling already did. Regression tests cover both orders.
- `docs/app.js:106,114,123`: generation tokens invalidate unfinished file reads
  after Reset/new selection. Chromium deliberately completes a deferred read
  after Reset and verifies the workspace stays empty and processing disabled.

No weakening of default Dry Run, environment switches, CLI confirmation,
non-demo consent scope, exclusions, bounds, campaign binding, locks or unknown
outcome handling. All HTTP tests are mocks; no real SMS, credentials, phone
integration or recipient lists were used.

## Applied pinned design skills

Read both actual installed SKILL.md files and guidelines. Pins remain
`5e85045d96662605f33e12150cdc6d00cb04dc0a`. Ran the full context loader: no
PRODUCT.md or DESIGN.md. Applied the brand register plus audit, layout,
typeset and polish references to this brand surface and its secondary tool.
Voice: careful, deliberate, practical. Retained the established plum/rose/paper
palette and system type under identity preservation. No new fonts, imagery
dependencies, frameworks, invented metrics or dashboard simulation were added.

The primary illustration is a semantic architecture figure, not a fabricated
phone screenshot. Native disclosures reveal OS commands and advanced operations.
Advanced sending is prose and a documentation link, not a copy-and-run card.

### Before UI findings (baseline file references)

`docs/index.html:5` — simulator-first hero and CTA obscure Python/Android setup.

`docs/style.css:1` — hero clamp reaches 4.55rem (72.8px), above the brief's scale.

`docs/index.html:13` — horizontally scrollable decisions lack keyboard focus.

`docs/index.html:13` — sr-only caption class is undefined in the shipped CSS.

`docs/app.js:71` — a consent conflict can still display a queued duplicate ID.

Portfolio `src/data/interactiveProjects.ts:175` — summary and category lead with
the simulator rather than installed software and external Android dependency.

### After UI audit

`docs/index.html:17` — Get Started → #install; Python identity and separate Android
requirement visible in the hero. Demo is a quiet tertiary action.

`docs/index.html:20,27` — prominent Android architecture/setup precedes major
Quick Start; installation precedes the retained stable #simulator anchor.

`docs/product.css:9` — hero capped at 56px desktop / 40px mobile; body remains
readable. Architecture labels retain separate lines on mobile.

`docs/index.html:63` — decisions region is focusable and named; caption hiding,
focus states and reduced-motion treatment are defined in product.css.

`docs/app.js` — literal textContent rendering, bounded CSV parsing and formula
escaping preserved. No network APIs, phone entry, analytics or persistence added.

Release browser review: zero axe A/AA violations at seven required widths,
no horizontal page overflow or broken assets/anchors. Existing table scroll is
intentional, named and keyboard-accessible. All seven arrival captures and the
Android/installation/demo interaction surfaces were reviewed; no mockups used.
Reviewer assessment: initial 16/20 → final 19/20 (a11y 4, performance 4,
responsive 4, tokens/single light theme 3, anti-patterns 4). This is a design
judgment, not a measured certification or a substitute for browser evidence.

## Verification

Baseline: 52 Python / 6 Node tests. Final: 56 Python tests with 98% coverage,
9 Node tests. Ruff E9/F63/F7/F82, compileall, pip check and pip-audit pass.
Default CLI is exercised by the existing socket-blocked subprocess regression
and reports preflight/summary, two simulations, zero gateway submissions.

Chromium/axe checks 320, 375, 390, 768, 1024, 1440 and 1920px: hierarchy,
OS disclosures, anchors, skip/focus, reduced motion, synthetic sample, conflicting
consent/opt-outs, invalid template, 1 MiB/1,000-row limits, export escaping,
literal HTML-like values and Reset race. No external requests or console errors.
The Pages verify job now runs this focused isolated suite before deployment;
runtime dependencies are unchanged. Artifacts are retained for 14 days.
The browser verification job pins Ubuntu 24.04, supported by the isolated
Playwright version. The first PR attempt exposed ubuntu-latest moving to an
unsupported 26.04 image; no application test or protection was relaxed.

Local Lighthouse: mobile 100/100/100/92; desktop 95/100/100/92
(performance/accessibility/best-practices/SEO). Local SEO notes missing root
robots.txt; no score-only change made. Final mobile line-spacing refinement does
not affect functionality. Docker/non-root/network-disabled checks remain in the
existing required Linux CI; the local Linux Docker daemon is unavailable.

Generated evidence is ignored and kept out of Docker/source publication.
Private portfolio changes are limited to this project and its specific CTA,
content, genuine website capture and related QA. No real sends, backend,
schedule, carrier bypass, unrelated project redesign or Mission 08 work.
