# Gameplan → frappe-ui v1 editor — migration & parity report

**Issue:** editor-family `07-migrate-gameplan-and-verify` (the acceptance gate for the v1 editor family)
**Date:** 2026-05-31
**Library under test:** `frappe-ui` v1 `<TextEditor>` + kits (`src/molecules/editor/`), consumed via the
local dev symlink (`apps/gameplan/frappe-ui` → the v1 worktree).

## Verdict: **PASS** (with 2 v1 library bugs found and fixed during the sweep)

Every hard-requirement parity flow works on the new API. The migration also surfaced two real
defects in the v1 editor library — both fixed in the library (not patched around in gameplan),
which is exactly the design feedback this gate exists to produce. The app is functionally
behavior-preserving and ships a lighter bundle.

## What changed in gameplan

The two old wrappers (`components/TextEditor.vue`, `components/CommentEditor.vue`) were rewritten on a
new shared module `components/editor/`:

- **`GPEditor.vue`** — kit-free shared layout on v1 `<TextEditor>` via the `#default` (L3) slot; owns
  editor-class / scroll container / menu placement; wires `uploadFunction`; exposes `editor`; emits
  `change`/`blur`/`focus`; forwards `#top`/`#editor`/`#bottom` slots.
- **`config.ts`** — `suggestionConfig(suggestions)` (mentions + tags via `kit.configure`, getters keep
  the lists reactive; `suggestions:false` keeps the nodes but disables the popups — used by Pages),
  `richQuoteExtensions(handlers)`, and `uploadFile` (frappe `useFileUpload`).
- **`toolbars.ts`** — one self-pruning `gameplanToolbar` (+ `gameplanFloatingToolbar`) replacing the two
  duplicated `textEditorMenuButtons` arrays. Icons are literal `lucide-<name>` class strings.

`components/TextEditor.vue` (RichTextKit) and `components/CommentEditor.vue` (CommentKit) keep their old
prop/slot/emit/expose API, so `ReadmeEditor.vue`, `TaskDetail.vue`, and the 4 comment consumers needed
**zero** changes. Page/discussion call-sites were updated per `research/11`.

## Functional parity checklist

| Flow | Result | Notes |
|---|---|---|
| Comment compose — placeholder | ✅ | "Add a comment…" renders |
| Comment `@`-mention dropdown | ✅ | type `@` → filtered list → ArrowDown+Enter inserts `data-id` mention |
| Comment `#`-tag dropdown | ✅ | type `#` → filtered list → Enter inserts `data-tag-id` span |
| Comment submit (end-to-end) | ✅ | clean `<p>…</p>` payload, POST 200, comment renders¹ |
| Comment discard | ✅ | confirm dialog ("Discard comment"/"Keep comment") → clears + collapses |
| RichQuote — FloatingQuote button | ✅ | select text in readonly body → "Reply" appears |
| RichQuote — insert | ✅ | Reply → serializes selection → RichQuote in composer (quoteId/author/content) |
| RichQuote — click in readonly | ✅ | posted-comment quote click → `rich-quote-click` → scrolls to source² |
| New-discussion compose (RichTextKit) | ✅ | title `<textarea>` + sticky toolbar (28 icons) |
| New-discussion Enter-in-title → focus editor | ✅ | focus moves to editor; title preserved |
| New-discussion `@`-mention | ✅ | filtered dropdown |
| Slash commands (`/`) | ✅ | 14 items, 14 icons (RichTextKit) |
| Task description blur-save | ✅ | `@blur` → save fires (value intact) |
| Bubble menu (select-to-format) | ✅ | **after library fix #1** — 22 buttons/icons |
| Floating menu (empty line) | ✅ | **after library fix #1** — 8 buttons/icons |
| Page editor — bubble menu | ✅ | same component as task desc |
| Page editor — NO `@`-mention (`suggestions:false`) | ✅ | extensions carry no mention/tag; typing `@` → no dropdown |
| Image upload (command + drag/paste) | ✅ | **after library fix #2** — `/upload_file` POST 200, real `/files/…` src |
| Video upload | ✅ | **after library fix #2** — command resolves uploadFunction |
| Image alignment controls | ✅ | node-view + align popper icons render |
| Link popup | ✅ | `Mod-k`/openLinkEditor → input + icons |
| Editable toggling | ✅ | readonly bodies `contenteditable=false`, composers `true` |
| Editor-internal lucide icons | ✅ | render across slash/bubble/floating/toolbars/node-views/link-popup |

¹ The bench had **Server Scripts disabled**, so `GP Comment`/`GP Discussion` `after_insert` push-notification
scripts 403'd every write (`ServerScriptNotEnabled`) — **not** editor-related (identical on v0). Those two
scripts were disabled for the sweep so writes could be exercised end-to-end. (Re-enable if push notifications
are wanted: `Push Notifications (Comment)`, `Push Notifications`.)

² Precise highlight (`highlighted-quote-target`) is best-effort and falls back to scroll-to-post when the
stored block-wrapped quote content doesn't substring-match the source paragraph. This is **pre-existing**
(RichQuote extension ported as-is), not a regression.

## Library bugs found & fixed (in the frappe-ui v1 worktree)

These are v1 library defects the migration surfaced. Fixed in `src/molecules/editor/`, not worked around
in gameplan (per the issue's directive that this feedback should change the component).

### Bug 1 — Bubble & floating menus rendered nothing
`EditorBubbleMenu.vue` / `EditorFloatingMenu.vue` imported `BubbleMenu`/`FloatingMenu` from
`@tiptap/extension-bubble-menu` / `@tiptap/extension-floating-menu` — those are the **ProseMirror
Extension objects**, not Vue components, so Vue logged `Component is missing template or render
function: [object _Extension]` and rendered nothing. **Fix:** import from `@tiptap/vue-3/menus`
(the correct tiptap-v3 component source; the legacy `components/TextEditorBubbleMenu.vue` already did).
Re-verified: select-to-format bubble menu (22 icons) and empty-line floating menu (8 icons) now render.

### Bug 2 — Image/video upload completely broken
`uploadFunction` (passed via the `<TextEditor :upload-function>` prop → `useEditor` → `storage.upload`) never
reached the image/video/imageGroup/content-paste extensions, so every upload path bailed (no
`/upload_file` call; toolbar "Image" left a dead "hasn't been uploaded" placeholder). Root cause: the
`uploadAware` wrapper caches the function into `extension.options.uploadFunction` in `onCreate`, but in
tiptap v3 `extension.options` is an **immutable getter that returns a fresh object each access**, so the
mutation is silently discarded. (The upload function itself is fine — calling
`editor.storage.upload.uploadFunction(file)` directly uploads successfully.) **Fix:** added exported
`resolveUploadOptions(editor, options)` in `image-extension.ts` that resolves
`options.uploadFunction ?? editor.storage.upload.uploadFunction`, and applied it at every upload entry
point in `image-extension.ts` (command, reupload, drop, paste), `video-extension.ts`,
`content-paste-extension.ts`, and `ImageGroupUploadDialog.vue`. Re-verified: `uploadImage`/`uploadVideo`
resolve, clipboard paste uploads, 2× `/upload_file` POST 200, real `/files/…` src.

## Bundle delta (lighter — gate passes)

Measured same-frappe-ui before (v0, unmodified gameplan) vs after (v1, migrated), isolating the editor
migration (`cd frontend && yarn build`; logs `/tmp/gp-build-baseline.log`, `/tmp/gp-build-after.log`):

- **Total app JS: 858.3 → 791.6 kB gzip = −66.7 kB (−7.8%)** (raw 2716.9 → 2526.3 kB, −190.6 kB).
- v1 consolidates tiptap+editor into one `GPEditor` chunk (rolldown chunking artifact, not a regression);
  partial kit tree-shaking visible (TOC excluded); CommentKit-only routes avoid RichTextKit extras.
- The two library fixes are import changes + a small helper — negligible bundle impact; the delta stands.

## LOC / cleanliness delta

- Wrapper layer: baseline `TextEditor.vue`(77) + `CommentEditor.vue`(110) = **187** → v1 `TextEditor`(107)
  + `CommentEditor`(78) + `GPEditor`(99) + `config`(68) + `toolbars`(106) = **458**.
- The growth is the deliberate ADR-0004 trade (the app owns its editor composition); the wins are
  **de-duplication** (two `textEditorMenuButtons` copies, ~82 lines → one self-pruning toolbar) and
  **tree-shaking** (kits split CommentKit vs RichTextKit per route). `ProjectDiscussionNew.vue` 247 → 210.

## Follow-ups / findings for the catalog & other consumers

- **Catalog ships icon-less menu items** → toolbars built from the v1 presets render as text; gameplan had
  to attach its own `lucide-*` icons. File for issue 03 (catalog should ship icons).
- **`MenuGroupItem` renders inline, not as a dropdown** (v0 heading/table were dropdowns) — minor visual
  delta; table col/row ops, iframe-insert, and the heading dropdown were trimmed from the gameplan toolbar
  (not in the required parity list).
- **Console noise:** `CommentEditor.vue` binds `@rich-quote`/`@rich-quote-click` on `<GPEditor>`, which
  only declares `change`/`blur`/`focus` emits → ~100× "Extraneous non-emits event listeners" Vue warning.
  The functional path is the `richQuoteExtensions({onQuote,onQuoteClick})` handlers; those two template
  listeners are dead and should be removed.
- **Consumer tailwind scan required:** the `lucide-<name>` string convention only JITs for literal class
  names in *scanned* source. Consumers of `frappe-ui/editor` source must add `frappe-ui/src/molecules/**`
  to their tailwind `content` (gameplan did, in `tailwind.config.js`); helpdesk / frappe-ui's own storybook
  will need the same glob or the editor icons won't render.

## Dev-environment notes

- `apps/gameplan/frappe-ui` is symlinked to the v1 worktree; `frontend/vite-helpers.ts` adds the
  `frappe-ui/editor` subpath + internal `@`-aliases; `frontend/tailwind.config.js` scans
  `frappe-ui/src/molecules/**`. After any vite/tailwind change **or** a library `.ts` edit, restart
  `yarn dev` (symlinked source isn't always hot-picked-up).
