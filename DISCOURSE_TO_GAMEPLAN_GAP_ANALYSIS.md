# discuss.frappe.io → Gameplan: Gap Analysis

**Scope assumed** (confirmed with stakeholder): _Full replacement_ — retire Discourse entirely, migrate all history, and **preserve public access + SEO ranking** (hard requirement). This is the most demanding of the possible migration shapes; every gap below is rated against it.

**Source system:** discuss.frappe.io runs **Discourse** (open-source forum). It is a public, Google-indexed, self-service Q&A community that has run since ~2014.

**Target system:** Gameplan — Frappe backend + Vue 3 SPA served at the auth-gated `/g` route. Product language: Community (`GP Team`) → Space (`GP Project`) → Discussion (`GP Discussion`) → Comment (`GP Comment`).

---

## 1. Verdict

**This is not a migration — it is building a public forum product on top of Gameplan.**

Gameplan and Discourse are different product categories. Discourse is a *public, anonymously-readable, SEO-indexed, self-moderating Q&A forum with open signup*. Gameplan is a *private, invite-only, login-gated team discussion tool*. The cosmetic feature gaps (badges, votes) are minor. The gaps that decide viability are **architectural**, and there are six of them, each individually a project:

1. No public/anonymous read and no SEO/crawlability (Gameplan is a login-only SPA).
2. No URL/redirect continuity (needed to keep years of Google ranking).
3. No Q&A / "solved" / accepted-answer model (the core value of a support forum).
4. No open self-signup and no built-in SSO (Gameplan is invite-only).
5. Almost no moderation / anti-spam tooling (a public open-signup forum *will* be attacked).
6. No reply-by-email / email-in and no per-post email notifications (only a digest).

**Honest recommendation:** treat "full public replacement" as a multi-quarter product build, not an import job — and seriously weigh whether opening Gameplan's security model to the anonymous internet is worth the risk to its existing private-team product. A phased approach (migrate low-risk / internal categories first, keep Discourse serving the public until parity is proven) is far safer than a big-bang cutover. See §7–8.

---

## 2. Scale of the source (why "just import it" is hard)

From discuss.frappe.io's public activity (last 30 days): ~234 new topics, ~1,226 posts, ~267 sign-ups, ~1,536 active users/month, and **43 admins + 159 moderators**. Extrapolated over ~10 years, the real corpus is on the order of **hundreds of thousands of posts and 100k+ user accounts**.

Implications:
- Import performance and data integrity matter (bulk insert, dedup, idempotency).
- The **159-moderator footprint** is a direct signal of how much anti-spam/moderation load a public Frappe forum carries — capability Gameplan does not have.
- The full-text index (`gameplan_search.db`, SQLite FTS5) must scale to the whole corpus.

---

## 3. Data-model mapping

| Discourse concept | Gameplan equivalent | Fit |
|---|---|---|
| Category (top level) | `GP Team` (Community) | ⚠️ rough |
| Subcategory | `GP Project` (Space) | ⚠️ Discourse allows topics directly in a category; Gameplan discussions must live in a Space, not a bare Community |
| Topic | `GP Discussion` | ✅ |
| First post | `GP Discussion.content` | ✅ |
| Reply post | `GP Comment` | ⚠️ flat; loses post-level "in reply to" structure |
| Post revision | Frappe `Version` (`track_changes`) | ✅ |
| Tag | `GP Tag` + `GP Tag Link` | ✅ |
| Like (❤) | `GP Reaction` (emoji) | ⚠️ semantics differ; Discourse likes feed trust/badges |
| Accepted answer (Solved) | — | ❌ **none** |
| Trust level (0–4) | — | ❌ none |
| Badge / gamification | — | ❌ none |
| Bookmark | `GP Bookmark` | ✅ (no reminders) |
| Poll | `GP Poll` | ✅ |
| Upload / attachment | Frappe `File` (HasAttachments mixin) | ✅ |
| Private message (DM) | — | ❌ none (GP Room/Chat scaffolding is incomplete) |
| Group | `GP Member` tables only | ⚠️ no standalone groups / @group mentions |
| Flag / report | — | ❌ none |
| Per-topic watch/track/mute | Space follow + unread tracking | ⚠️ partial |
| User | Frappe `User` + `GP User Profile` | ✅ (no reputation) |
| Category/topic security | Community/Space `is_private` + membership | ✅ for private; ❌ for the *public* case |

Existing migration scaffolding in the repo: **`Discourse ID Map`** doctype (maps `reference_doctype`/`reference_name` ↔ `discourse_table`/`discourse_id`) and `gameplan/migrate_from_discourse/emojis.py` (emoji-name → unicode). **There is no actual importer yet** — this is a stub.

---

## 4. Feature gap table

Legend: 🔴 Blocker (migration fails without it) · 🟠 Major · 🟡 Minor · 🟢 Parity

| Area | Discourse | Gameplan today | Gap |
|---|---|---|---|
| **Public anonymous read** | Yes; core | Login-only; router redirects guests to `/login` | 🔴 |
| **SEO / crawlability** | SSR crawler HTML, sitemaps, canonical, OpenGraph, schema.org Q&A | Client-rendered SPA, no meta/robots/sitemap | 🔴 |
| **URL continuity / redirects** | `/t/slug/:id`, `/t/slug/:id/:post` permalinks | New SPA routes; no redirect map | 🔴 |
| **Solved / accepted answer** | Core (Q&A) | None; only close/pin | 🔴 |
| **Open self-signup** | Yes | Invite-only | 🔴 |
| **SSO / social login** | DiscourseConnect, OAuth, social | Depends on site config; not in-app | 🟠 |
| **Moderation: flag/report queue** | Review queue, flags | None | 🔴 |
| **Anti-spam** | Akismet, rate limits, TL0 sandbox | None | 🔴 |
| **User suspend/silence** | Yes | Only disable Frappe User | 🟠 |
| **Reply-by-email / email-in** | Yes | None | 🔴 |
| **Per-post email notifications** | Yes | Digest only (weekly/fortnightly/monthly) | 🟠 |
| **Trust levels** | 0–4, auto-promote, gate perms | None | 🟠 |
| **Badges / reputation** | Yes | Display-only 3-mo counts | 🟡 |
| **Per-topic notify (watch/track/mute)** | Yes | Space follow + unread only | 🟠 |
| **Private messages (DM)** | Yes | None | 🟠 |
| **Groups + @group mention** | Yes | Membership only; `@everyone` | 🟠 |
| **Nested/threaded replies** | Linear + "in reply to" links | Flat comments; rich-quote notify only | 🟠 |
| **Code blocks + syntax highlight** | Yes (critical for a dev forum) | TipTap editor — verify highlight support | 🟠 (verify) |
| **Link previews (onebox)** | Yes | Likely none | 🟡 |
| **RSS feeds (per category/tag)** | Yes | None | 🟡 |
| **Wiki posts (community-editable)** | Yes | `GP Page`, but not post-level wiki | 🟡 |
| **Topic timers / auto-close / slow mode** | Yes | Manual close/pin only | 🟡 |
| **Search** | Full-text + advanced filters | SQLite FTS5 + filters | 🟢 (good) |
| **Reactions / emoji** | Likes (+reactions plugin) | Emoji reactions + custom emoji | 🟢 |
| **Polls** | Built-in | `GP Poll` | 🟢 |
| **Attachments/uploads** | Yes | Yes | 🟢 |
| **Edit history / revisions** | Yes | Yes (`track_changes`) | 🟢 |
| **Bookmarks** | Yes | Yes | 🟢 |
| **Tags** | Yes | Yes | 🟢 |
| **Mobile / PWA** | Yes | First-class (PWA + iOS wrapper) | 🟢 |
| **Data importer** | — | Only `Discourse ID Map` stub | 🔴 (must build) |

---

## 5. The blockers, in depth

### 5.1 Public read + SEO + crawlability (the crux)
Gameplan serves a client-rendered Vue SPA at `/g` behind an auth guard (`frontend/src/router.ts` ~739; `gameplan/www/g.py`/`g.html` expose no content to `Guest`, no `robots`/`canonical`/`og:`/sitemap). A public forum needs:
- **Anonymous read** of public communities/spaces/discussions — a new permission tier below `Gameplan Guest` (which is itself an *authenticated* role). This touches every `has_permission` / `permission_query_conditions` path in `gameplan/permissions.py` + `hooks.py`.
- **Server-rendered, crawlable HTML** for every public discussion (Discourse ships a no-JS crawler view). Options: an SSR/pre-render layer, or Frappe `www`-served read-only pages for discussions that hydrate into the SPA. This is net-new architecture.
- **Sitemaps, canonical URLs, OpenGraph, and schema.org `QAPage`/`DiscussionForumPosting`** markup — without these, Google ranking will not transfer.

Opening the app to anonymous traffic also changes Gameplan's threat model (rate-limiting, caching, DoS surface) for its existing private-team customers. This is the single largest and riskiest workstream.

### 5.2 URL continuity / 301 redirects
SEO ranking is attached to existing Discourse URLs (`/t/:slug/:id`). To keep it you must: (a) mint **stable, public, human-readable URLs** for Gameplan discussions, and (b) build a **redirect table** old→new. The `Discourse ID Map` doctype is the right foundation — populate it during import and drive 301s from it. Also need per-post anchors (`/t/:slug/:id/:post`) mapping to comment anchors.

### 5.3 Q&A / accepted answer
A support forum's value is "question → accepted solution." Gameplan has no `accepted_answer`/`is_solved` concept (only close/pin). Needs: a field on `GP Discussion`, a "mark as solution" action on `GP Comment` (topic-owner + staff), solved badges/filtering, and schema.org markup for the accepted answer. Moderately sized backend + UI feature.

### 5.4 Open signup + SSO
Full replacement means the world must be able to register. Gameplan is invite-only (`GP Invitation`, admin-gated `invite_by_email`). Needs an open registration flow (email verification, terms/guidelines acceptance, TL0 sandbox equivalent) and ideally DiscourseConnect-style SSO parity so existing accounts map cleanly.

### 5.5 Moderation + anti-spam
159 moderators today is the tell. Public + open-signup = spam and abuse. Gameplan has only soft-delete, close, archive, and admin-delete. Needs: flag/report doctype + review queue, spam heuristics/Akismet, rate limits, user silence/suspend, and a new-user sandbox. Without this, a public launch is operationally unsafe.

### 5.6 Email-in + per-post notifications
Many forum users reply by email and expect immediate per-post email. Gameplan has inbound email = none and outbound = digest + invites only (`gameplan/email_digest.py`). Needs a Frappe `Communication`/`Email Account` inbound pipeline (`append_to`, `In-Reply-To` threading) and opt-in per-post transactional mail.

---

## 6. What already fits well (leverage these)
- **Content core**: discussions, comments, reactions, polls, attachments, revisions, tags, mentions — all present and close in spirit.
- **Search**: SQLite FTS5 with permission filtering and per-doctype scoring already indexes discussion/comment/page/task.
- **Mobile/PWA**: first-class, including an iOS wrapper.
- **Read/unread + bookmarks + drafts**: mature.
- **Import anchor**: `Discourse ID Map` gives idempotent old↔new mapping for both data and redirects.

---

## 7. Migration mechanics (once the product gaps are closed)
1. **Extract** from Discourse Postgres (or its DB export): users, groups, categories, subcategories, topics, posts, tags, likes, solved markers, uploads, PMs.
2. **Map**:
   - Category → `GP Team`; Subcategory → `GP Project`. Top-level categories that hold topics directly need a default landing Space.
   - Topic → `GP Discussion`; first post → `content`; replies → `GP Comment`.
   - Users → Frappe `User` + `GP User Profile` (avatars, bios). Passwords can't transfer — plan SSO or reset-on-first-login.
   - Tags, likes→reactions, polls, uploads→File, revisions.
   - Record every mapping in `Discourse ID Map` for redirects + idempotent re-runs.
3. **Rewrite content**: Discourse Markdown/BBCode/oneboxes → Gameplan TipTap HTML; internal `/t/...` links → new links; image/upload URLs rehosted.
4. **Redirects**: generate 301 map from `Discourse ID Map`.
5. **Reindex** search; verify counts (topics/posts/users) against source.
6. **Dry-run on a copy**, validate a sample of high-traffic threads by hand, then cut over with Discourse kept read-only as a safety net.

---

## 8. Rough effort & phasing

Ordered by "must exist before a public cutover":

- **Phase 0 — Decide**: confirm Gameplan (vs. staying on Discourse) is the right target given §1. This is a strategic call, not an engineering one.
- **Phase 1 — Public/SEO foundation** (largest): anonymous read tier + SSR/crawlable pages + sitemaps/canonical/OG + public URL scheme + redirect engine.
- **Phase 2 — Forum semantics**: Q&A/accepted answer, open signup + SSO, per-topic notification levels.
- **Phase 3 — Safety**: moderation queue, flags, anti-spam, suspend/silence, rate limits.
- **Phase 4 — Comms**: email-in + per-post email.
- **Phase 5 — Importer**: build the real Discourse → Gameplan importer on the `Discourse ID Map` foundation; dry-run; validate; cut over.
- **Ongoing / nice-to-have**: trust levels, badges, DMs, groups, RSS, oneboxes, code-highlight verification.

Each of Phases 1–5 is a substantial slice (backend + UI). Phase 1 alone changes core architecture and security posture.

---

## 9. Open questions to resolve before building
- Can Gameplan's private-team product safely coexist with an anonymous-public mode on the same install, or does the public forum need an isolated deployment?
- Is a full-SSR forum surface acceptable, or a pre-render/read-only-page hybrid?
- SSO strategy for 100k+ existing accounts (DiscourseConnect parity vs. reset-on-login)?
- Does the TipTap editor render fenced code with syntax highlighting at forum quality (verify)?
- Is losing user-to-user DMs acceptable, or must they migrate?
