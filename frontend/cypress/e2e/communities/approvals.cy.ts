import { resetData, type SeedIds } from '../../support/seed'

function moderation(ids: SeedIds) {
  cy.visit(`/g/community/${ids.community}/moderation`)
  cy.contains('button', /^\s*Approvals\s*$/).click()
}
function policy(ids: SeedIds, count = 3) {
  cy.request('POST', '/api/method/gameplan.approval_policy.set_policy', {
    community: ids.community,
    count,
  })
}
function newDiscussion(ids: SeedIds, title: string) {
  cy.visit(`/g/community/${ids.community}/new-discussion?spaceId=${ids.space}`)
  cy.get('textarea[placeholder="Title"]').type(title)
  cy.get('[contenteditable=true]').click().type('Approval browser evidence')
  cy.contains('button:visible', /^\s*Publish\s*$/).click()
}
function reply(ids: SeedIds, text: string, privateSpace = false) {
  cy.visit(
    `/g/community/${ids.community}/space/${privateSpace ? ids.private_space : ids.space}/discussion/${ids.discussion}`,
  )
  cy.contains('button', 'Add a comment').click()
  cy.get('[contenteditable=true]').click().type(text)
  cy.contains('button:visible', /^\s*Submit\s*$/).click()
  cy.contains('Submitted for moderator approval.').should('be.visible')
}
function selectStatus(value: string) {
  cy.get('[role="combobox"]').click()
  cy.contains('[role="option"]', value).click()
}

describe('Post approval', () => {
  it('opens discussion and reply composers when randomUUID is unavailable', () => {
    cy.on('window:before:load', (win) => {
      Object.defineProperty(win.crypto, 'randomUUID', { value: undefined })
    })
    resetData('space_with_discussion').then((ids) => {
      newDiscussion(ids, 'Discussion without randomUUID')
      cy.contains('Discussion without randomUUID').should('be.visible')
      cy.visit(`/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}`)
      cy.button('Add a comment').click()
      cy.get('[contenteditable=true]').click().type('Reply without randomUUID')
      cy.button('Submit').click()
      cy.contains('Reply without randomUUID').should('be.visible')
      cy.button('Add a comment').should('be.visible')
    })
  })

  it('configures first-N approval, holds a draft privately, and publishes once under its author', () => {
    resetData('space_with_discussion').then((ids) => {
      moderation(ids)
      cy.contains('button', 'Approval settings').click()
      cy.get('[role="dialog"] input[type="checkbox"]').check()
      cy.get('[role="dialog"] input[type="number"]').should('have.value', '3').clear().type('1')
      cy.contains('button', 'Save approval policy').click()
      cy.contains('Approval policy saved.').should('be.visible')
      cy.switchUser('secondMember')
      newDiscussion(ids, 'Held discussion from UI')
      cy.location('pathname').should('eq', '/g/submissions')
      cy.contains('Held discussion from UI').should('be.visible')
      cy.contains('button', 'View submission').click()
      cy.get('[role="dialog"]').contains('Approval browser evidence').should('be.visible')
      cy.get('body').type('{esc}')
      cy.request('/api/method/gameplan.approvals.queue').then(({ body }) => {
        const id = body.message.items[0].name
        cy.switchUser('member')
        cy.request({ url: `/api/v2/document/GP Submission/${id}`, failOnStatusCode: false })
          .its('status')
          .should('eq', 403)
      })
      cy.visit(`/g/community/${ids.community}/discussions`)
      cy.contains('Held discussion from UI').should('not.exist')
      cy.switchUser('admin')
      moderation(ids)
      cy.contains('button', /^\s*Review\s*$/).click()
      cy.get('[role="dialog"]')
        .contains('button:not([role="combobox"])', /^\s*Approve\s*$/)
        .click()
      cy.contains('No pending submissions.').should('be.visible')
      cy.request('/api/method/frappe.auth.get_logged_user')
        .its('body.message')
        .should('eq', 'Administrator')
      cy.switchUser('secondMember')
      cy.visit('/g/submissions')
      selectStatus('Approved')
      cy.contains('button', 'View submission').click()
      cy.get('[role="dialog"]').contains('a', 'Open published post').click()
      cy.contains('Held discussion from UI').should('be.visible')
      cy.contains('Approval browser evidence').should('be.visible')
      newDiscussion(ids, 'Publishes after first approval')
      cy.location('pathname').should('include', '/discussion/')
      cy.contains('Publishes after first approval').should('be.visible')
    })
  })

  it('queues replies, requires rejection feedback, and lets the author withdraw another submission', () => {
    resetData('space_with_discussion').then((ids) => {
      policy(ids)
      cy.switchUser('secondMember')
      reply(ids, 'Reply awaiting approval')
      cy.contains('.comments-timeline', 'Reply awaiting approval').should('not.exist')
      cy.switchUser('admin')
      moderation(ids)
      cy.contains('button', /^\s*Review\s*$/).click()
      cy.get('[role="dialog"] [role="combobox"]').click()
      cy.contains('[role="option"]', 'Reject').click()
      cy.get('[role="dialog"]')
        .contains('button:not([role="combobox"])', /^\s*Reject\s*$/)
        .should('be.disabled')
      cy.get('[role="dialog"] textarea').type('Please add a reproducible example')
      cy.get('[role="dialog"]')
        .contains('button:not([role="combobox"])', /^\s*Reject\s*$/)
        .click()
      cy.contains('No pending submissions.').should('be.visible')
      cy.switchUser('secondMember')
      cy.visit('/g/submissions')
      selectStatus('Rejected')
      cy.contains('button', 'View submission').click()
      cy.contains('Please add a reproducible example').should('be.visible')
      cy.get('body').type('{esc}')
      reply(ids, 'Another pending reply')
      cy.visit('/g/submissions')
      cy.contains('button', 'View submission').click()
      cy.contains('button', 'Withdraw submission').click()
      cy.get('[role="dialog"]')
        .last()
        .contains('button', /^\s*Withdraw\s*$/)
        .click()
      cy.contains('No pending submissions.').should('be.visible')
      selectStatus('Withdrawn')
      cy.contains('button', 'View submission').click()
      cy.contains('Another pending reply').should('be.visible')
    })
  })

  it('lets an invited Guest track a private-Space submission on mobile without gaining settings access', () => {
    resetData('private_space_with_guest').then((ids) => {
      policy(ids)
      cy.viewport(390, 844)
      cy.switchUser('guest')
      reply(ids, 'Private Guest submission', true)
      cy.visit('/g/submissions')
      cy.contains('button', 'View submission').click()
      cy.contains('Private Guest submission').should('be.visible')
      cy.get('body').type('{esc}')
      cy.visit(`/g/community/${ids.community}/moderation`)
      cy.contains('Approval settings').should('not.exist')
      cy.contains('Only Community moderators can open this page.').should('be.visible')
    })
  })
})
