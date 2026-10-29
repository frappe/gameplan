import { resetData } from '../../support/seed'

function appoint(community: string) {
  cy.request('POST', `/api/v2/document/GP Team/${community}/method/set_member_moderator`, {
    user: 'member2@example.com',
    is_moderator: 1,
  })
}
const rows = () => cy.get('[data-testid="history-row"]')
function action(url: string, body: object = {}) {
  cy.window().then((win) =>
    cy.request({
      method: 'POST',
      url,
      body,
      headers: { 'X-Frappe-CSRF-Token': (win as any).csrf_token },
    }),
  )
}

describe('Community moderation history', () => {
  it('opens discussion history from its menu and retains reversed actions', () => {
    resetData('space_with_discussion').then((ids) => {
      appoint(ids.community!)
      cy.switchUser('secondMember')
      cy.visit(
        `/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}/${ids.discussion_slug}`,
      )
      cy.selectDropdownOption('Discussion Options', 'Moderation history')
      cy.url().should('include', 'kind=discussion')
      cy.contains('No moderation history.').should('be.visible')
      const endpoint = `/api/v2/document/GP Discussion/${ids.discussion}/method/`
      action(endpoint + 'hide', { reason: 'Off-topic history reason' })
      action(endpoint + 'restore')
      action(endpoint + 'delete_spam', { reason: 'Spam history reason' })
      cy.reload()
      rows().should('have.length', 3)
      rows().first().should('contain.text', 'Delete Spam')
      rows().should('contain.text', 'Restore').and('contain.text', 'Off-topic history reason')
      rows().should('contain.text', 'By Second Member')
      cy.contains('Seed content').should('not.exist')
      cy.reload()
      rows().should('have.length', 3)
    })
  })

  it('opens reply history without exposing stored text', () => {
    resetData('space_with_discussion').then((ids) => {
      appoint(ids.community!)
      cy.request('POST', '/api/v2/document/GP Comment', {
        reference_doctype: 'GP Discussion',
        reference_name: ids.discussion,
        content: '<p>History original body sentinel</p>',
      }).then(({ body }) => {
        const name = body.data.name
        cy.switchUser('secondMember')
        const endpoint = `/api/v2/document/GP Comment/${name}/method/`
        cy.request('POST', endpoint + 'hide', { reason: 'Reply history reason' })
        cy.request('POST', endpoint + 'restore')
        cy.visit(
          `/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}/${ids.discussion_slug}`,
        )
        cy.get(`div[data-id="${name}"] button[aria-label="Comment Options"]`).click()
        cy.contains('[role="menuitem"]', 'Moderation history').click()
        cy.url().should('include', 'kind=reply')
        rows().should('have.length', 2).and('contain.text', 'Reply history reason')
        cy.contains('History original body sentinel').should('not.exist')
      })
    })
  })

  it('filters Community ban history by user and denies ordinary members', () => {
    resetData('space_with_discussion').then((ids) => {
      appoint(ids.community!)
      cy.switchUser('secondMember')
      const endpoint = '/api/method/gameplan.community_bans.set_ban'
      cy.request('POST', endpoint, {
        community: ids.community,
        user: 'member@example.com',
        banned: 1,
        reason: 'Ban history reason',
      })
      cy.request('POST', endpoint, {
        community: ids.community,
        user: 'member@example.com',
        banned: 0,
      })
      cy.visit(`/g/community/${ids.community}/moderation`)
      cy.contains('button', /^History$/).click()
      rows().should('have.length', 2)
      cy.get('[role="combobox"]').click()
      cy.contains('[role="option"]', 'User bans').click()
      cy.get('input[placeholder="All users"]').type('member@example.com')
      cy.contains('button', 'Apply filters').click()
      cy.url().then((url) =>
        expect(new URL(url).searchParams.get('target')).to.eq('member@example.com'),
      )
      rows().should('have.length', 2).and('contain.text', 'Ban history reason')
      cy.get('input[placeholder="All users"]').clear().type('missing@example.com')
      cy.contains('button', 'Apply filters').click()
      cy.contains('No moderation history.').should('be.visible')
      cy.switchUser('member')
      cy.visit(`/g/community/${ids.community}/moderation?tab=history`)
      cy.contains('Only Community moderators can open this page.').should('be.visible')
      cy.request({
        url: `/api/method/gameplan.moderation_history.history?community=${ids.community}`,
        failOnStatusCode: false,
      })
        .its('status')
        .should('eq', 403)
    })
  })
})
