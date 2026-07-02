# Public Web Execution Plan: Guest SPA + Crawler Pages

Make Gameplan discussions publicly readable with the **same SPA experience for
guests** and a **lightweight HTML view for crawlers**, so it can replace
discuss.frappe.io without losing SEO. Architecture and rationale:
`PUBLIC_WEB_ARCHITECTURE.md` (v2). Product gaps beyond public access (solved
answers, open signup, moderation, email-in): `DISCOURSE_TO_GAMEPLAN_GAP_ANALYSIS.md`.

**Principles**

- **Security first, everywhere.** Anonymous read is opt-in twice: a site-level
  master switch (`gameplan_public_web_enabled` in site config) AND per-space
  `visibility = Public Web`. Switch off → the whole feature is inert. Guest
  gets zero write paths. Every phase ships existence-leak tests (private
  content must 404 identically to nonexistent content).
- **Same components, same API.** Guests read through the existing permission
  hooks (`has_permission` / `permission_query_conditions`), not a parallel
  public API. No forked data paths in components.
- **Content never differs by user-agent.** Crawlers get a lighter *rendering*
  of the same fields. A drift check keeps the two surfaces honest.
- **Each phase is a vertical slice with a browser-verifiable outcome and a
  manual review gate.** STOP after every phase. One PR per phase.
- **Verification discipline:** backend tests run in CI (not on the dev site);
  browser verification in incognito against the demo site; crawler surface
  verified with `curl -A Googlebot`.
- **Don't build ahead of the switch.** Nothing in these phases changes
  behavior for existing private/member sites when the master switch is off —
  assert this in tests each phase.

**Dependencies on parallel tracks** (not in this plan, required before full
discuss.frappe.io cutover): Discourse importer, open signup + SSO, moderation/
anti-spam, solved/accepted-answer, email-in. Phase 6 is coupled to the
importer; everything else is independent.

---

## Phase 1 — Anonymous read tier: guest opens one public discussion

**Goal:** in an incognito window, a logged-out visitor can open a discussion
in a `Public Web` space via its `/g/...` URL and read it (rough edges
allowed). Private spaces remain invisible. Master switch off → everything
redirects to `/login` exactly as today.

Backend:
- Add `visibility` (Select: `Private` / `Members` / `Public Web`, default
  `Members`) to `GP Project`; patch maps existing `is_private` → `Private`,
  else `Members`. Keep `is_private` in sync (or deprecate it in a follow-up —
  decide at review).
- Master switch helper `gameplan.public_web.is_enabled()` reading site config.
- Extend permission layer for the anonymous `Guest` session, read-only, scoped
  to `Public Web` spaces: `gameplan/permissions.py`
  (`team_query_conditions`, `project_query_conditions`) and the per-doctype
  `get_permission_query_conditions` / `has_permission` for GP Discussion,
  GP Comment, GP Poll (`hooks.py:117–135`). Role permissions for Guest on
  these doctypes (read only) so `/api/v2` document reads resolve.
- GP User Profile: guest-readable display fields only (name, image) — audit
  what the discussion page actually fetches and expose the minimum.
- Explicitly out of guest scope: GP Task, GP Page, GP Draft, GP Notification,
  GP Unread Record, GP Bookmark, soft-deleted comments (`deleted_at`).

Frontend (minimal):
- Router guard (`frontend/src/router.ts` ~739): when boot says public web is
  enabled, allow the discussion route for guests; everything else still
  redirects to `/login`.
- `gameplan/www/g.py::get_boot`: emit `is_public_visitor` + public-web flag;
  guest path skips session-only boot work; don't `capture()` telemetry per
  anonymous hit.

Tests (CI):
- Guest reads public discussion/comments ✓; private/Members space discussion
  → same error shape as nonexistent name ✓; guest write attempts (comment,
  reaction, poll vote) rejected ✓; switch off → guest reads rejected ✓;
  member/admin behavior unchanged ✓.

Verify in browser: incognito → public discussion renders; private URL → 404;
logged-in user sees no change.

**Size: L.** This is the security-critical phase — request extra review here.
**STOP for review.**

---

## Phase 2 — Full guest browsing: the read-only app

**Goal:** a guest can browse the whole public tree — space list, discussion
lists, discussions, profiles — and every write affordance becomes a login CTA.

- Sidebar (`AppSidebar.vue`) and space/discussion lists render only public
  spaces for guests (the permission layer already filters; fix anything that
  assumes a session — unreads, drafts, bookmarks, notifications).
- Read-only affordances: comment editor, reactions, bookmark, poll voting →
  "Log in to participate" CTA (one shared component). Hide new-discussion,
  drafts, notifications, tasks, pages nav for guests.
- Skip Socket.IO connection for guests; app degrades gracefully without
  realtime.
- Guest-safe error handling: expired/invalid session anywhere → login CTA,
  not a crash.
- Cypress spec: guest browsing journey on the demo site (public space seeded
  via `test_api`).

Verify in browser: full incognito walk of the public tree; click every
affordance; nothing 500s, nothing leaks private spaces.

**Size: M–L. STOP for review.**

---

## Phase 3 — Public URLs + per-route meta: `/t/<slug>/<id>`

**Goal:** discussions have permanent public URLs in Discourse's scheme, and
any URL shared in Slack/Discord/iMessage unfurls with real title/description.

- Router base rework: SPA serves both `/g/*` (app) and `/t/*`, `/c/*` (public
  content) — base `/` with two route trees, or equivalent. Confirm PWA
  manifest + iOS wrapper assumptions survive (`www/g.html`, `ios/`).
- `website_route_rules` (`hooks.py:67`): add `/t/<path>` and `/c/<path>` → `g`.
- URL resolution: `/t/<slug>/<id>` → discussion (native id for now; Discourse
  ID Map lands in Phase 6). Wrong slug → canonical redirect. Logged-in users
  on `/t/...` see the discussion in full app chrome (no redirect).
- Per-route meta injection in `g.py::get_context` for public routes: `<title>`,
  meta description (first-post excerpt), `<link rel="canonical">`, OG/Twitter
  tags into `g.html`. Non-public routes keep the static shell.
- SPA share/copy-link actions emit the public `/t/...` URL for public spaces.

Verify: `curl https://<site>/t/<slug>/<id>` shows correct meta without JS;
paste a link into a Slack DM and see the unfurl; navigation works logged-in
and logged-out.

**Size: M. STOP for review.**

---

## Phase 4 — Crawler HTML view

**Goal:** `curl -A "Googlebot" /t/<slug>/<id>` returns complete, valid HTML —
content, paginated comments, structured data — with no JavaScript.

- New module `gameplan/public_web/`: `PublicPageRenderer` registered via the
  `page_renderer` hook (`frappe/website/path_resolver.py:56` — Builder's
  mechanism). Active only for declared crawler UAs on `/t/`, `/c/`, `/latest`.
- Topic template: title, breadcrumb, first-post HTML, comments paginated
  ~20/page (`?page=N`, per-page canonical, prev/next), author name/avatar,
  ISO dates. Render-time sanitization pass on content HTML (defense in depth).
- Structured data: `DiscussionForumPosting` + `BreadcrumbList` JSON-LD.
  (`QAPage`/`acceptedAnswer` upgrade when the solved feature ships.)
- Listing templates for `/c/<slug>/<id>` and `/latest`; `noindex,follow` on
  deep pagination. Deleted/archived → **410 Gone**.
- Caching: Frappe guest page cache; invalidate topic + affected listing pages
  on GP Discussion / GP Comment write events.
- Drift guard in CI: render one seeded discussion via SPA API and crawler
  view; assert text-content equivalence.

Verify: `curl -A Googlebot` a seeded 50-comment topic (check pagination);
Google Rich Results test on the JSON-LD; normal browser UA still gets the SPA.

**Size: M. STOP for review.**

---

## Phase 5 — Scale plumbing: sitemaps, robots, hardening

**Goal:** the public surface survives crawl storms and tells crawlers exactly
what to index.

- Custom sitemap index (built-in `www/sitemap.py` caps out at 50k URLs/file):
  `/sitemap.xml` → chunked `topics-<n>.xml` from public-space discussions
  (`lastmod = last_post_at`) + categories sitemap; scheduled regeneration,
  cached.
- `robots.txt`: allow `/t/`, `/c/`; disallow `/g/`, `/api/`, `/login`.
- Rate limiting for anonymous requests (Frappe rate limiter + nginx/CDN
  guidance documented for deployment).
- CDN caching for crawler pages (cookie-free by construction) with
  purge-on-write; short-TTL guidance for guest API responses if needed.
- Load sanity check: scripted anonymous crawl of a seeded site (a few
  thousand topics), watch worker/DB behavior.

**Size: M. STOP for review.**

---

## Phase 6 — Discourse URL compatibility + files (importer-coupled)

**Goal:** every migrated Discourse URL resolves — topic URLs byte-for-byte,
the rest via explicit redirects. Blocked on importer populating
`Discourse ID Map`; build against synthetic map entries until then.

- `/t/<slug>/<id>` resolution consults `Discourse ID Map`
  (`discourse_table='topics'`) before native ids. Post permalinks
  `/t/<slug>/<id>/<n>` → map (`posts`) → `#comment-<name>` anchor (SPA scroll
  + crawler-view page calculation).
- Redirect map for `/u/<user>`, `/tag/<tag>`, `/c/<old-category>`, feed URLs →
  301 to equivalents or 410. Never soft-404.
- **Files policy (decide before the importer writes files):** Discourse
  uploads land as *public* Frappe Files for public spaces; new uploads to
  Public Web spaces default public; permission-checked proxy route as
  fallback for stragglers. Audit that no `/private/files/*` URL appears in
  public page HTML.

**Size: M (plus importer coordination). STOP for review.**

---

## Phase 7 — Launch ops & cutover

**Goal:** discuss.frappe.io traffic lands on Gameplan with rankings intact.

- Dedicated site for the community forum (recommended in the architecture
  doc); master switch on there only.
- Pre-cutover: full-corpus dry run; spot-check top-100 traffic URLs
  (Search Console export) resolve correctly; Rich Results + sitemap
  validation; log-based 404/410 audit on a staging crawl.
- Cutover: DNS switch; Discourse to read-only (safety net, keep for a
  quarter); submit sitemaps in Search Console; monitor coverage, crawl
  stats, and top-query rankings weekly.
- Rollback plan: DNS back to Discourse (read-only lifted); Gameplan keeps
  running for logged-in users.

**Size: S–M, ongoing monitoring.**

---

## Phase sizes at a glance

| Phase | Slice | Size |
|---|---|---|
| 1 | Anonymous read tier (security core) | L |
| 2 | Full guest browsing UX | M–L |
| 3 | Public URLs + meta injection | M |
| 4 | Crawler HTML view | M |
| 5 | Sitemaps, robots, hardening | M |
| 6 | Discourse URLs + files | M |
| 7 | Launch ops | S–M |

Critical path: 1 → 2 → 3 → 4 → 5; 6 overlaps with importer work; 7 last.
Phases 3+4 can start once 1 is merged if staffing allows (2 only touches
affordances).

## Open decisions (resolve at phase reviews)

- Phase 1: keep `is_private` synced vs. migrate fully to `visibility`.
- Phase 3: exact router base strategy (`/` base vs. alternative) after
  checking PWA/iOS constraints.
- Phase 4: RSS feeds (`/latest.rss`, per-category) in scope or later.
- Phase 5: CDN choice/config ownership (app guidance vs. deployment concern).
- Global: public search page for guests (FTS5 exists; SEO doesn't need it).
