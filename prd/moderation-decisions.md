# Moderation decisions

Owner: Ebrahim. Decisions updated: 2026-10-17.

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
- This slice covers discussion replies. Discussion-level actions, reports, sanctions, automated filtering, bulk actions, and migration follow later.
- Combined verification: 140 backend tests, two browser tests, Ruff, Prettier, and a production frontend build passed on 2026-10-17.

## Decisions still open

Plan these when their implementation slice is next. Roadmap recommendations do not settle them.

- Ordinary members' editing rights and whether a Community can opt into forum-specific rules.
- Discussion-level hide/remove/restore behavior and further attachment handling.
- Audit history UI and retention policy.
- Report reasons, resolution behavior, and review queue workflow.
- Silence and suspension behavior, scope, and expiry.
- Approval rules, posting limits, slow mode, watched-word matching, and censor behavior.
- Bulk action selection, progress, partial failures, and undo behavior.

## Keeping this log current

Add confirmed decisions after each planning round.
Record later changes against the original decision ID with the date and replacement decision.
Keep unresolved questions and implementation choices distinct from confirmed product decisions.
