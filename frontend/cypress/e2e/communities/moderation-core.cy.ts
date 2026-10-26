import { resetData } from '../../support/seed'

const moderationPath = (community: string) => `/g/community/${community}/moderation`

function appointModerator(community: string) {
  cy.request('POST', `/api/v2/document/GP Team/${community}/method/set_member_moderator`, {
    user: 'member2@example.com',
    is_moderator: 1,
  })
}

function confirmRemoval(label: string) {
  cy.get('[role="dialog"] textarea').type('Spam review')
  cy.get('[role="dialog"]').contains('button', label).click()
}

describe('Community moderation core', () => {
  it('removes private Space management actions for a banned member while keeping reading available', () => {
    resetData('private_space_with_guest').then((ids) => {
      const path = `/g/community/${ids.community}/space/${ids.private_space}/discussions`
      cy.switchUser('member')
      cy.visit(path)
      cy.get('button[aria-label="Space actions"]').should('be.visible')
      cy.switchUser('admin')
      cy.request('POST', '/api/method/gameplan.community_bans.set_ban', {
        community: ids.community,
        user: 'member@example.com',
        banned: 1,
        reason: 'Read only',
      })
      cy.switchUser('member')
      cy.visit(path)
      cy.get('button[aria-label="Space actions"]').should('not.exist')
      cy.location('pathname').should('eq', path)
      cy.contains('Secret thread').should('be.visible')
    })
  })

  it('hides a discussion, protects readers, and restores it from Removed content', () => {
    resetData('space_with_discussion').then((ids) => {
      appointModerator(ids.community!)
      const path = `/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}/${ids.discussion_slug}`
      cy.switchUser('secondMember')
      cy.visit(path)
      cy.selectDropdownOption('Discussion Options', 'Hide discussion')
      confirmRemoval('Hide discussion')
      cy.contains('h1', 'Community moderation').should('be.visible')
      cy.contains('Spam review').should('be.visible')
      cy.contains('button', 'Preview').click()
      cy.contains('Seed content').should('be.visible')

      cy.switchUser('member')
      cy.visit(path)
      cy.contains('Seed content').should('not.exist')
      cy.contains(/Page not found|Discussion not found/).should('exist')

      cy.switchUser('secondMember')
      cy.visit(moderationPath(ids.community!))
      cy.contains('button', 'Restore').click()
      cy.get('[role="dialog"]').contains('button', 'Restore').click()
      cy.contains('No removed content.').should('be.visible')
      cy.visit(path)
      cy.contains('Seed content').should('be.visible')
    })
  })

  it('removes only the selected spam reply and restores its original text', () => {
    resetData('space_with_discussion').then((ids) => {
      appointModerator(ids.community!)
      cy.request('POST', '/api/v2/document/GP Comment', {
        reference_doctype: 'GP Discussion',
        reference_name: ids.discussion,
        content: '<p>Spam reply sentinel</p>',
      }).then(({ body }) => {
        const reply = () => cy.get(`div[data-id="${body.data.name}"]`)
        cy.switchUser('secondMember')
        cy.visit(
          `/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}/${ids.discussion_slug}`,
        )
        reply().find('button[aria-label="Comment Options"]').click()
        cy.contains('[role="menuitem"]', 'Delete spam').click()
        confirmRemoval('Delete spam')
        reply().should('contain.text', 'This reply was removed by a moderator.')
        reply().should('not.contain.text', 'Spam reply sentinel')
        cy.visit(moderationPath(ids.community!))
        cy.get('[role="combobox"]').click()
        cy.contains('[role="option"]', 'Replies').click()
        cy.contains('Spam removed').should('be.visible')
        cy.contains('button', 'Preview').click()
        cy.contains('Spam reply sentinel').should('be.visible')
        cy.contains('button', 'Restore').click()
        cy.get('[role="dialog"]').contains('button', 'Restore').click()
        cy.contains('No removed content.').should('be.visible')
      })
    })
  })

  it('keeps a banned Space out of the composer while allowing another Community', () => {
    resetData('two_communities').then((ids) => {
      const community = ids.communities![0]
      cy.request('POST', '/api/method/gameplan.community_bans.set_ban', {
        community,
        user: 'member@example.com',
        banned: 1,
        reason: 'Posting restriction test',
      })
      cy.switchUser('member')
      cy.visit(`/g/community/${community}/new-discussion?spaceId=${ids.spaces![0]}`)
      cy.get('textarea[placeholder="Title"]').type('Draft in a banned Community')
      cy.contains('button', 'Publish').should('be.disabled')
      cy.contains('button[aria-haspopup="listbox"]', 'Select Space').filter(':visible').click()
      cy.contains('[role="option"]', 'Alpha Space').should('not.exist')
      cy.contains('[role="option"]', 'Beta Space').click()
      cy.contains('button', 'Publish').should('not.be.disabled')
    })
  })

  it('bans and unbans participation while retaining reading access', () => {
    resetData('space_with_discussion').then((ids) => {
      appointModerator(ids.community!)
      cy.switchUser('secondMember')
      cy.visit(moderationPath(ids.community!))
      cy.contains('button', 'Community bans').click()
      cy.get('[role="combobox"]').click()
      cy.contains('[role="option"]', /^Member$/).click()
      cy.contains('button', 'Ban from Community').click()
      confirmRemoval('Ban')
      cy.contains('button', 'Lift ban').should('be.visible')

      cy.switchUser('member')
      cy.visit(
        `/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}/${ids.discussion_slug}`,
      )
      cy.contains('Seed content').should('be.visible')
      cy.contains('You are banned from participating').should('be.visible')
      cy.contains('button', 'Add a comment').should('not.exist')
      cy.visit(`/g/community/${ids.community}/space/${ids.space}/discussions`)
      cy.contains('Welcome thread').should('be.visible')
      cy.contains('button', 'Add new').should('not.exist')
      cy.visit(`/g/community/${ids.community}/new-discussion?spaceId=${ids.space}`)
      cy.contains('No space to post in').should('be.visible')
      cy.get('textarea[placeholder="Title"]').should('not.exist')
      cy.window()
        .then((win) =>
          cy.request({
            method: 'POST',
            url: '/api/v2/document/GP Comment',
            headers: { 'X-Frappe-CSRF-Token': (win as any).csrf_token },
            failOnStatusCode: false,
            body: {
              reference_doctype: 'GP Discussion',
              reference_name: ids.discussion,
              content: 'Banned API reply',
            },
          }),
        )
        .then((response) => {
          expect(response.status).to.eq(403)
          expect(JSON.stringify(response.body)).to.include('PermissionError')
        })

      cy.switchUser('secondMember')
      cy.visit(moderationPath(ids.community!))
      cy.contains('button', 'Community bans').click()
      cy.contains('button', 'Lift ban').click()
      cy.get('[role="dialog"]').contains('button', 'Lift ban').click()
      cy.contains('No active Community bans.').should('be.visible')
      cy.switchUser('member')
      cy.visit(
        `/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}/${ids.discussion_slug}`,
      )
      cy.contains('button', 'Add a comment').should('be.visible')
    })
  })
})
