# Timed Community bans and account suspensions

Community bans retain reading access and block participation in that Community.
Global admins can suspend an account across every installed app on the Frappe site.
Both controls accept an indefinite duration, 1 hour, 24 hours, 168 hours, 720 hours,
or a custom date and time. The picker names the viewer's timezone.

## Enforcement and storage

`GP User Restriction` stores one current record per Community/user pair, or per
user for site suspension. Authorization reads its indexed identity and compares
the UTC deadline on every request. Request caching avoids repeated state queries.
Expiry does not wait for a scheduled job. Changing the site's timezone does not
change the deadline. An independent `User.enabled` setting remains authoritative.

Password login and authenticated session, API-key, and OAuth requests share the
suspension check. Session cleanup runs after commit in batches of 100. The Node
realtime handler disconnects the target account on suspension, scoped to its site.
Its suspension-event subscription disconnects sockets if the subscription fails.

Actions require a reason and append actor, time, and previous/new expiry to
`GP Moderation Log`. A bounded job records each automatic expiry once. Community
moderators see their Community's history; account suspension history is global-only.
The affected account receives the scope, reason, and expiry by queued email.
Community reasons and deadlines also appear to the affected person in the app.
Published content and pending submissions are preserved.

## Deployment

Run `bench --site <site> migrate`, build the frontend, and restart web, worker,
scheduler, and Node realtime processes. Migration preserves legacy Community bans
as indefinite restrictions and skips history without a Community scope.

The schema migration does not delete content or change `User.enabled`. Before
rolling back the code, reconcile timed bans and site suspensions: old code does
not recognize their expiry or enforce the separate site-suspension state.

Migration from Discourse, flood limits, and separate silence controls remain later work.

## Verification

- 88 focused backend tests passed, including real cookie/API-key/password authentication,
  timezone and DST checks, legacy-ban backfill, and bounded expiry cleanup.
- 10 browser tests passed across the new controls and existing moderation core.
- The realtime target-room/disconnection test, production build, and repository checks passed.
- The full backend run also exposed inherited linked-user null-field assertions,
  lazy-report-evidence assertions, and a search query-budget assertion. The evidence
  and query-budget failures reproduce on the unchanged watched-words parent branch.
