# Moderation decisions

Owner: Ebrahim. Decisions updated: 2026-10-22.

This log records choices Ebrahim confirmed in this chat.
The roadmap describes sequencing and contains proposals for later features.
A recommendation becomes a decision only after Ebrahim accepts it.

## Confirmed decisions

| ID | Decision | Consequence |
| --- | --- | --- |
| D01 | Ebrahim owns moderation end to end, including product decisions, backend, and frontend. | No separate maintainer decision gate or documentation-only contract PR is required. Normal code review still applies. |
| D02 | Migration is a later workstream. | Production inventory, mappings, importer changes, historical data, and cutover do not block moderation development. |
| D03 | Use grill-me whenever planning moderation work. | Discuss the next concrete slice in focused rounds. Ebrahim makes the decisions. |
| D04 | Prefer implementation PRs below 1,000 changed lines. | Include tests in the size estimate. Split larger changes into useful pieces. |
| D05 | The first version appoints moderators per Community, covering its Spaces. | Individual Space appointments and groups are deferred. |
| D06 | Community admins and global admins appoint and remove moderators. | Community admins act only within their own Community. Global admins can act across Communities. |
| D07 | Moderator status grants no membership administration, Community settings access, or authority to appoint moderators. | Moderator assignment remains separate from Community administration. Existing admin authority stays intact. |
| D08 | Moderators need existing access to a private Space before moderating its content. | Appointment does not reveal private Spaces or their content. |
| D09 | Only existing Community members can be appointed. | Add a person to the Community before appointing them. Removing membership removes moderator authority. |
| D10 | The first implementation covers assignment/removal, a shared backend permission check, a small assignment UI, and tests. | Hide/remove actions, reports, sanctions, and changes to ordinary editing rights follow separately. |
| D11 | Bundle moderator assignment and manual reply Hide/Restore in one PR. Push to Ebrahim's fork without opening the PR yet. | This replaces D10's separate PR boundary. |
| D12 | Hiding affects only the selected reply. | Copied quotations remain independent content and require separate moderation. |
| D13 | Readers and the author see a neutral placeholder. Authorized moderators can preview the stored body and restore it. | Appointment does not grant private-Space access. Hidden text is excluded from search and ordinary revision access. |
| D14 | Complete T27 (moderation core: hide, ban, delete spam) within the existing PR #621. | This expands the reply-only scope. D15–D20 define discussion hiding, Community bans, and reversible spam deletion. |
| D15 | Include discussion Hide/Restore as well as reply Hide/Restore. | A hidden discussion and its replies are unavailable to ordinary readers. Authorized moderators with existing Space access can inspect and restore them. |
| D16 | Community moderators can ban participation within their Community. | Banned users can still read otherwise-accessible content and participate elsewhere. Only global admins can disable accounts site-wide. |
| D17 | Delete spam is reversible. | Remove spam from ordinary lists, search, and access while preserving restricted originals that authorized moderators can restore. Permanent destruction remains a separate admin operation. |
| D18 | Community bans last until manually lifted and survive leaving and rejoining. | Block creating, editing, deleting, reactions, voting, and invitations in that Community. Preserve reading and membership. Staff must lose their Community role before being banned; global admins are exempt. |
| D19 | Add a moderator-only Removed content view per Community with preview and Restore. | Ordinary feeds/search omit removed discussions; direct access shows a neutral unavailable message. Replies show neutral placeholders. Private-Space restrictions still apply. |
| D20 | Delete spam requires a reason and affects only the selected reply or discussion. | Preserve descendants/files and closed/pinned state for restoration without new notifications. Do not automatically ban the author or remove other posts. Ordinary Delete remains separate. |
| D21 | Build T26 moderation history in a separate PR after the T27 review fixes. | Reuse the immutable log for discussion/reply action history and Community-scoped user ban/unban history. Include actor, time, reason, pagination, existing moderator/private-Space access rules, frontend, and tests. |
| D25 | Start T16 reporting and a basic Pending/Resolved moderator queue with manual decisions. | Discussion and reply reporting ships end to end. Automatic hiding, trust weighting, and migration remain separate. |
| D26 | Members and invited Guests may report accessible content unless banned from participating in its Community. | Anonymous reports, self-reports, and reports on already hidden/removed targets are excluded. |
| D27 | Report reasons are Spam, Abuse/inappropriate, Off-topic, AI-generated, and Other. | Notes are optional, limited to 500 characters, and required for Other. Reasons trigger manual review only. |
| D28 | One pending review groups reports for each target. | Each authenticated reporter has at most one active report per target. Moderators review the reports together. |
| D29 | Review decisions are Dismiss, Uphold while keeping visible, Hide, and Delete spam. | Require a decision note, resolve the grouped reports together, reuse existing moderation actions, and never automatically ban the author. |
| D30 | Each report preserves the reported title/body version. | Only authorized moderators with current Space access may see identities, notes, and snapshots. Authors and other reporters cannot read the evidence. |
| D31 | A new report after resolution opens a fresh review, including for previous reporters. | Limit new reports to 10 per account per hour across the site. Duplicate reports in an active review reuse the existing report without consuming quota. |

D05–D07 were confirmed in the first answer accepting scope and assignment authority.
D08–D10 were confirmed in the next answer accepting private access, eligibility, and the first PR boundary.

## First-slice implementation notes

These describe the implementation. They are not additional product decisions confirmed through grilling.

- The appointment uses `GP Member.is_moderator` on a Community membership row.
- Assignment and removal use the existing Community member menu.
- `can_moderate_space()` combines existing Space access with Community moderator or admin authority.
- Removing or leaving the Community deletes the appointment with the membership row.
- Rejoining creates an ordinary membership and does not restore the appointment.
- A Community merge does not copy moderator appointments into the destination Community.
- Role display prioritizes Community Admin when a member also has a moderator appointment.
- Verification passed: 17 moderator tests, 28 existing Community tests, and one browser test.
- Verification used the new disposable site `moderation-test.localhost`. Existing sites were not migrated or reset.

Implementation: `gameplan/gameplan/doctype/gp_team/gp_team.py`, `gameplan/permissions.py`, and the Community member UI.
Tests: `gameplan/tests/features/test_moderators.py` and `frontend/cypress/e2e/communities/moderators.cy.ts`.

## Hide/Restore implementation notes

- These are implementation choices, not additional confirmed product decisions.
- Hide requires a reason of at most 500 characters. Restore needs no new reason.
- A restricted, immutable `GP Moderation Log` stores the original text, action, actor, time, and hide reason. Global admins can read the log; scoped moderators preview the current hidden body through the reply action.
- The reply row stores a placeholder while hidden. Ordinary saves cannot hide, restore, edit, or move a hidden reply.
- Repeated Hide or Restore requests are idempotent. Restoring does not send new mention notifications.
- Private attachments follow the hidden reply's permissions. A reply with public attachments must have those files made private before Hide succeeds; public static URLs cannot enforce reply permissions.
- Search excludes hidden reply results and disables shared-vocabulary spelling corrections because that vocabulary retains removed words.
- This first slice covered discussion replies. D15–D20 extend the same PR to complete T27.
- Combined verification: 140 backend tests, two browser tests, Ruff, Prettier, and a production frontend build passed on 2026-10-17.

## T27 implementation notes

- Discussion and reply Hide/Restore share one implementation. Delete spam records a separate, reversible state.
- Removal stores a placeholder on the live row and preserves the original in restricted moderation history.
- Discussion removal protects replies, polls, revisions, search results, and attachments through the parent discussion.
- Removed content has a paginated moderator view. Private-Space access still applies to each result and action.
- Community bans use immutable Ban/Unban history, independent of membership. Community staff must lose their role before a ban.
- Server checks cover content writes, reactions, votes, moves, invitations, and attached uploads. Banned readers retain access.
- The current user's ban list drives the read-only UI. A user-scoped realtime event refreshes that list after a ban changes.
- Frappe's supported File controller override applies the moderation policy to downloads, ZIP reads, and file mutations, including uploader/share access.
- Public attachments must become private before removal. Existing independent copies and previously downloaded bytes remain outside removal.
- Embedded polls follow their reply's removal state for reads, lists, voting, public HTML, and private attachments. Explicit poll shares must be removed before moderation; removed polls cannot receive new shares.
- Discussion removal and restoration notify affected users' other tabs after commit, including read notification lists whose unread count stays unchanged.
- Restoration preserves descendants, closed/pinned state, and existing notification records. It queues reply reindexing without new mention notifications.
- Reports, trust levels, automatic filtering, bulk actions, moderation history UI, and migration remain separate tasks.

## Decisions still open

Plan these when their implementation slice is next. Roadmap recommendations do not settle them.

- Ordinary members' editing rights and whether a Community can opt into forum-specific rules.
- Audit history UI and retention policy.
- Temporary bans, automatic expiry, and separate silence behavior.
- Approval rules, posting limits, slow mode, watched-word matching, and censor behavior.
- Bulk action selection, progress, partial failures, and undo behavior.

## Keeping this log current

Add confirmed decisions after each planning round.
Record later changes against the original decision ID with the date and replacement decision.
Keep unresolved questions and implementation choices distinct from confirmed product decisions.

## T16 implementation notes

- GP Review groups reports by discussion/reply and records one immutable resolution. GP Report preserves each reporter's original evidence and note.
- Submission is session-bound, deduplicated, and limited to 10 reports per rolling hour across the site. Indexed locking reads serialize account quotas and target review decisions.
- Queue and evidence access follow current Community/Space permissions. Pages contain at most 40 reviews/reports, and each response includes only one selected evidence body.
- Resolving a review checks the content version and current scope before applying existing Hide/Delete spam actions. Dismiss and Uphold preserve content state. Conflicting decisions require refresh.
- The UI includes report dialogs, Pending/Resolved queues, current author/content, reported versions, and a link to the full discussion. No automatic hiding, banning, notifications, or trust weighting is added.
- Fresh installation, migration, 71 backend tests, and eight browser tests passed. Four MariaDB concurrency tests are included but skipped on the local SQLite site; they require MariaDB CI.

## Review integrity implementation notes

- These are implementation choices that enforce the existing ban and review rules.
- A Community ban also blocks Space management, including moves, merges, and permanent deletion. Reading and management elsewhere remain available.
- Pending reports block permanent deletion of their target, including parent cascades, and moving replies outside discussions. Resolve the reports before either operation.
- Review versions include embedded poll questions, options, and voting settings. Poll votes do not invalidate a content review.
