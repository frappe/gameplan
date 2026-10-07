# Permission scenarios in the demo fixture

The existing fixture covers all nine active combinations of Community and Space visibility.
It keeps the original people, content, images, and discussions. It does not use the legacy `is_private` flag or membership status.

## Active tier matrix

| Community tier | Space tier | Existing example | Logged-out access |
|---|---|---|---|
| Anonymous | Anonymous | Common Room / Game Design, Art, Releases | Read only |
| Anonymous | General | Common Room / Engineering | Denied |
| Anonymous | Member Access | Common Room / Audio & Music | Denied |
| General | Anonymous | Community & Marketing / Player Feedback | Denied |
| General | General | Community & Marketing / Creators & Press | Denied |
| General | Member Access | Community & Marketing / Marketing | Denied |
| Member Access | Anonymous | Studio / Watercooler | Denied |
| Member Access | General | Studio / Announcements | Denied |
| Member Access | Member Access | Studio / People Ops | Denied |

Logged-out access also requires `gameplan_public_access_enabled=1` and `gameplan_demo_enabled=0`.
An Anonymous Space does not make its General or Member Access Community public.

## Test accounts

All addresses use `@moonhollow.studio`. Set passwords locally after seeding. The fixture does not store passwords.

| Account | Scenario and expected access |
|---|---|
| maya | Global admin. Can manage every Community and Space. |
| chloe | Community & Marketing admin. Can manage its General and Anonymous Spaces, but not Common Room. |
| priya | Studio member. Can read Announcements and Watercooler, but cannot manage them. |
| priya | Non-member of Community & Marketing. Can read Player Feedback and Creators & Press, but not Marketing. |
| priya | Common Room member without Audio & Music membership. Cannot read Audio & Music. |
| sam | Audio & Music member. Can read and manage that Member Access Space. |
| dev | Non-member of Studio. Cannot read Studio, Announcements, Watercooler, or People Ops. |
| felix | Gameplan Guest with eight explicit Space grants. Can read granted Spaces, including the private Studio shell. |
| felix | No grant in Community & Marketing or Project Bluebird. Cannot read their non-public Spaces or manage any Community or Space. |
| jonas | Project Bluebird member. Can read its archived Community and content. |

Only global admins automatically manage every Space.
Members of Member Access Spaces can manage their Space without being Community admins.

## Archived cases

QA & Playtests has the Anonymous tier inside Common Room, but the fixture archives it after replaying its content.
Logged-out visitors cannot read it. Authorized signed-in users can read it but cannot add content while it is archived.

Project Bluebird remains Member Access and is archived after replay.
Its Anonymous-tier Prototype Builds Space remains non-public.

## Manual state-change flows

Use separate browser sessions for Maya, the affected account, and a logged-out visitor.
Test direct URLs as well as the sidebar. Restore each change before the next case.

1. Remove Sam from Audio & Music. Verify that Sam loses read and manage access. Add Sam again.
2. Remove Felix's three Studio grants. Verify that Felix loses the Studio shell and its Spaces. Restore the grants.
3. Add Dev to Studio. Verify access to Announcements and Watercooler, but not People Ops. Remove Dev again.
4. Join Community & Marketing as Priya. Verify that Marketing still requires its own Space membership. Leave the Community again.
5. Change Common Room from Anonymous to General. Verify that every Space closes to logged-out visitors. Restore Anonymous.
6. Change Game Design from Anonymous to General, then Member Access. Check anonymous, member, non-member, and guest access after each change.
7. Move Game Design to Studio. Verify that its Anonymous tier does not bypass the private Community. Move it back.
8. Archive Common Room. Verify that its public Community and Spaces disappear for logged-out visitors. Unarchive it.
9. Unarchive QA & Playtests. Verify that logged-out read access returns, while posting still requires login. Archive it again.
10. Disable the site's public-access switch. Verify that logged-out access closes without changing the stored tiers. Enable it again.
11. Remove Chloe's Community admin flag. Verify that management actions disappear for its General and Anonymous Spaces. Restore the flag.
12. Invite a new Gameplan Guest. Verify that accepting an invitation does not grant sibling Spaces or management rights.

## Automated checks

Run the seed permission tests on a disposable site, not the manual test site:

```sh
bench --site gp-suite.test run-tests --app gameplan --module gameplan.tests.platform.test_demo_permissions
bench --site gp-suite.test run-tests --app gameplan --module gameplan.tests.platform.test_demo_fixture
```

The tests check the nine active tier combinations, role boundaries, archives, grant and membership revocation, moves, and public-access switches.
The existing permission tests cover the remaining controller and API paths.

The generator clears Gameplan records before replay. Back up the site before running it.
Archive events run after the content replay, through the existing controller methods.
