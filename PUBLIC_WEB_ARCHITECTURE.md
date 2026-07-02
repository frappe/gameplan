# Public, Crawlable Gameplan: Architecture Deep-Dive (v2)

Companion to `DISCOURSE_TO_GAMEPLAN_GAP_ANALYSIS.md` §5.1–5.2.

**v2 revision:** requirement upgraded — anonymous visitors must get the **same UI/UX as logged-in users** (the real SPA), not a simplified read-only page. This matches Discourse's actual behavior: Discourse serves its full Ember SPA to logged-out humans; its server-rendered HTML view is for *declared crawlers only*. v1's "Jinja pages for guests" design is therefore demoted to the bot layer.

---

## 1. Where Gameplan stands today (grounded)

- `/g/<path>` → one www page via `website_route_rules` (`hooks.py:67`). `gameplan/www/g.py` renders `g.html` — a Jinja shell injecting boot JSON + the Vite SPA bundle. `no_cache = 1`.
- `g.html` has zero SEO surface: static `<title>`, no description/canonical/OG/JSON-LD.
- SPA router redirects logged-out users to `/login`; every API read is permission-gated to authenticated Gameplan roles (`permissions.py`, `hooks.py:117–135`). `Gameplan Guest` is an authenticated role — there is no anonymous tier.
- **Content is stored as HTML** (TipTap) in `GP Discussion.content` / `GP Comment.content`.
- Frappe primitives verified in this bench: **`page_renderer` hook** (`frappe/website/path_resolver.py:56`, how Builder serves published pages), `website_redirects`, built-in `www/sitemap.py` / `robots.py`, guest page caching.

---

## 2. The architecture in one picture

```
                    ┌─ human (any session state) ──► g.html + SPA  (same UI/UX for everyone;
Request /t/slug/123 ┤                                guests see read-only affordances)
                    └─ declared crawler UA ────────► crawler HTML view (Jinja, ~50KB,
                                                     cached; DiscussionForumPosting JSON-LD)
```

- **Humans — logged in or not — get the SPA.** Guests run the same components against the same API, scoped by a new anonymous-read permission tier. Same UI/UX by construction.
- **Declared crawlers get lightweight server-rendered HTML** (Discourse's exact mechanism). UA-keyed serving of *equivalent* content is the industry-standard, non-penalized pattern; cloaking risk only arises when bot content *differs* from human content.

### Why not the alternatives

**Full Vue SSR + hydration** ❌ — Node render service at request time next to a Python stack (no slot in Frappe Cloud's model); frappe-ui's `useList`/`useDoc` have no serialize/resume support; browser assumptions throughout (`localStorage` boot, Socket.IO, DOM refs). Months of isomorphic refactoring for first-paint speed nobody asked for.

**Prerender all public pages** (the "make snapshots the architecture" version) ❌ as the primary mechanism, ✅ as an optional future bot layer:
- **Hidden dependency:** a prerenderer is a headless browser visiting pages as an anonymous user. Until the guest SPA + anonymous API tier exist, that browser gets redirected to `/login`. Prerendering *depends on* the guest SPA; it cannot substitute for it.
- **Build-time prerender is infeasible** at this scale: 100k+ topic pages, ~40 new posts/day → permanent staleness or perpetual rebuilds.
- **On-write (ISR-style) prerender is feasible** — ~40 renders/day ongoing is trivial; one-time backfill ≈ 300k page-renders × ~2s ÷ 4 workers ≈ ~2 days of headless-Chrome time. But its output is only useful to bots: serving snapshots to humans without hydration means the SPA mounts and replaces the DOM (flash, dead controls until JS loads) — strictly worse than the fast guest SPA. So on-write prerender competes only with the Jinja crawler view, and loses on infra (Puppeteer worker, snapshot store, invalidation) vs. a cached template. Revisit if crawler-template drift ever becomes a real maintenance burden.
- **No HTML layer at all** (trust Googlebot JS rendering) is too risky as the sole mechanism: render-queue latency across 100k+ URLs during the migration window, and AI crawlers (GPTBot, ClaudeBot, PerplexityBot) largely don't execute JS — material for a dev forum in 2026.

---

## 3. Workstream A — the guest-capable SPA (the real work)

This is where "same UI/UX" is earned, and where the security cost lives: same components + same API means **anonymous users must be able to read Gameplan's API** for public content.

### A1. Public visibility tier
- `GP Project.visibility`: `Private` / `Members` (today's default) / **`Public Web`** — opt-in per space + site-level master switch (`gameplan_public_web_enabled`). Public-web communities follow from their spaces.
- Extend the existing `has_permission` / `permission_query_conditions` hooks so the anonymous `Guest` session gets **read-only** access to GP Team / GP Project / GP Discussion / GP Comment / GP Poll / GP User Profile (display fields only) — scoped strictly to `visibility == 'Public Web'` spaces.
- Why extend the permission layer rather than add a parallel `public_api` namespace: a parallel namespace forks every data path in the frontend (components would fetch differently per session state), defeating "same components, same API". Discourse's anon reads flow through the same API as members'; do the same.
- Non-negotiables: `Guest` gets **zero write paths**; drafts/tasks/pages/unreads/notifications stay out of scope; soft-deleted comments excluded; **existence-leak tests** (private space → identical 404-shape as nonexistent); master-switch-off means the tier is inert.

### A2. Boot + router + UI affordances
- `g.py::get_context` guest path: skip CSRF/session-only boot fields, emit a `is_public_visitor` boot flag, don't `capture()` telemetry per anonymous hit.
- Router (`router.ts` guard ~739): allow public route trees for guests when the site is public; everything else still redirects to `/login`.
- Read-only affordances: reply box / react / bookmark render as "Log in to participate" CTAs; sidebar shows public spaces only; Socket.IO skipped for guests (no realtime needed; degrade gracefully).
- New public route namespace served by the SPA: `/t/<slug>/<id>` (+ `/c/<slug>/<id>` listings). Requires router base rework (base `/` with `/g/*` and `/t/*` trees, or equivalent). Logged-in users on `/t/...` just see the discussion in full app chrome — no redirect dance.

### A3. Per-route meta injection in `g.html`
Even with a crawler view, SPA-served pages need unfurls + canonicals: `get_context` resolves the requested path (route rules already pass `app_path`) → inject `<title>`, meta description, `<link rel="canonical">`, OG/Twitter tags server-side for public routes. This also covers link previews in Slack/Discord/iMessage, which don't run JS.

### A4. Anonymous-traffic hardening
- Rate-limit anonymous API + page requests (nginx/CDN + Frappe rate limiter).
- Guest API responses: no per-user state → cacheable at short TTL if needed; DB reads are cheap (indexed lookups) but crawl storms at 100k pages are real.
- Render-time sanitization pass on content HTML for the public path (defense in depth — XSS on the anonymous web ≫ XSS inside an auth-gated app).

---

## 4. Workstream B — the crawler HTML layer

Custom `page_renderer` class (`gameplan.public_web.renderer`), active only for declared crawler UAs on public routes:

- **URL scheme mirrors Discourse byte-for-byte**: `/t/<slug>/<id>` resolved through **`Discourse ID Map`** (`discourse_table='topics'`) → migrated topics keep their URLs exactly; **zero 301s** for the corpus carrying the SEO value. Native discussions get sequential public IDs under the same scheme. Stale slug → 301 to canonical. Post permalinks `/t/<slug>/<id>/<n>` → ID map (`posts`) → `#comment-<name>` anchor. `/u/<user>`, `/tag/<tag>`, feeds → explicit 301/410 map, never soft-404s.
- **Page anatomy**: title + space breadcrumb, first-post HTML, comments paginated ~20/page (`?page=N`, per-page canonical, prev/next links), author names/avatars, ISO dates, `DiscussionForumPosting` + `BreadcrumbList` JSON-LD — upgraded to `QAPage`/`acceptedAnswer` once the solved feature (gap analysis §5.3) ships. Deleted/archived → **410 Gone**.
- **Listing pages** for `/c/...` and `/latest` so crawlers discover topics; `noindex,follow` on deep pagination.
- Cached via Frappe's guest page cache, invalidated on `GP Comment`/`GP Discussion` write events; CDN-cacheable (cookie-free by construction).
- Drift guard: a CI check rendering one seeded discussion through both surfaces and asserting text-content equivalence.

## 5. Shared plumbing

- **Sitemaps**: built-in `sitemap.xml` won't scale past 50k URLs/file — custom sitemap index → chunked `topics-<n>.xml` (from public-space GP Discussions, `lastmod = last_post_at`, scheduled regeneration + cache). `robots.txt`: allow `/t/`, `/c/`; disallow `/g/`, `/api/`, `/login`.
- **Private-files trap** ⚠️: discussion images under `/private/files/*` 403 for guests *and* Googlebot. Importer must write Discourse uploads as **public files** for public spaces (they were public already); new uploads to Public Web spaces default public; permission-checked proxy as fallback. Decide **before** the importer writes files.
- **Launch ops**: Search Console, structured-data validation, crawl-budget + 404/410 log monitoring through cutover.

---

## 6. Work breakdown

| # | Workstream | Size | Notes |
|---|---|---|---|
| A1 | Anonymous read permission tier | **L** | Security-critical; the heart of the project |
| A2 | Guest boot/router/affordances + `/t/` routes in SPA | M–L | Router base rework included |
| A3 | Per-route meta injection in `g.html` | S–M | Also fixes unfurls for members |
| A4 | Rate limiting, caching, sanitization | M | |
| B | Crawler renderer + templates + Discourse URL compat | M | Reuses v1 design; ID-map coupled |
| 5 | Sitemap index, robots, files policy | M | Files decision blocks importer |
| — | Launch ops | S, ongoing | |

Sequencing: A1 → A2/A3 in parallel → A4 → B → sitemaps/files with the importer. Rough shape: **~2 engineers for a few months** — moderately more than v1's Jinja-only design, with A1 (not rendering) as the long pole and the piece deserving the most review.

## 7. Open questions

- Dedicated site for discuss.frappe.io vs. public mode on shared product deployments? (Recommend dedicated site regardless; the `Public Web` tier + master switch keeps the feature safe for product installs either way.)
- Guest experience of search: FTS5 exists; expose a public search page in v1 or defer? (SEO doesn't need it.)
- RSS feeds (`/latest.rss`, per-category) — cheap on the crawler renderer; v1 or later?
- Router base rework (`/` vs `/g`) — confirm no PWA/iOS wrapper assumptions break.
