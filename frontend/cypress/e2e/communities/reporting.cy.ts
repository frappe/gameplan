import { resetData, type SeedIds } from '../../support/seed'
const thread = (ids: SeedIds) =>
  `/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}/${ids.discussion_slug}`
function reports(ids: SeedIds) {
  cy.visit(`/g/community/${ids.community}/moderation`)
  cy.contains('button', /^Reports$/).click()
}
function submitReport(reason = 'Spam', note = '') {
  cy.get('[role="dialog"] [role="combobox"]').click()
  cy.contains('[role="option"]', reason).focus().type('{enter}')
  cy.get('[role="listbox"]').should('not.exist')
  if (note) cy.get('[role="dialog"] textarea').type(note)
  cy.get('[role="dialog"]').contains('button', 'Submit report').click()
  cy.contains('Report submitted for moderator review.').should('be.visible')
}
function decision(value: string, note = 'Moderator reviewed the reports') {
  cy.get('[role="dialog"] [role="combobox"]').click()
  cy.contains('[role="option"]', value).click()
  cy.get('[role="dialog"] textarea').type(note)
  cy.get('[role="dialog"]').contains('button', 'Resolve review').click()
}

describe('Content reports', () => {
  it('previews reported polls read-only in current and reported content, including after Hide', () => {
    resetData('space_with_discussion').then((ids) => {
      const poll = { title: 'Reported poll', options: [{ title: 'Yes' }, { title: 'No' }] }
      cy.request('POST', '/api/v2/document/GP Comment', {
        reference_doctype: 'GP Discussion',
        reference_name: ids.discussion,
        content: `<div data-type="poll" data-poll-draft='${JSON.stringify(poll)}'></div>`,
      }).then(({ body }) => {
        cy.switchUser('secondMember')
        cy.request('POST', '/api/method/gameplan.reporting.submit', {
          doctype: 'GP Comment',
          name: String(body.data.name),
          reason: 'Spam',
        })
      })
      cy.switchUser('admin')
      reports(ids)
      cy.contains('button', /^Review$/).click()
      cy.get('[role="dialog"] [data-node-view-wrapper]')
        .should('have.length', 2)
        .each(($preview) => {
          cy.wrap($preview).contains('Reported poll').should('be.visible')
          cy.wrap($preview)
            .find('[role="radio"]')
            .should('have.length', 2)
            .each(($answer) => {
              cy.wrap($answer).should('be.disabled')
            })
        })
      cy.get('[role="dialog"] button[aria-label="Poll Options"]').should('not.exist')
      decision('Hide')
      cy.contains('No pending reports.').should('be.visible')
      cy.get('[role="dialog"]').should('not.exist')
      cy.get('[role="combobox"]').click()
      cy.contains('[role="option"]', 'Resolved').click()
      cy.contains('button', /^Review$/).click()
      cy.get('[role="dialog"] [data-node-view-wrapper]')
        .should('have.length', 1)
        .contains('Reported poll')
        .should('be.visible')
      cy.get('[role="dialog"] [role="radio"]').each(($answer) => {
        cy.wrap($answer).should('be.disabled')
      })
    })
  })

  it('lets an invited Guest report a private discussion', () => {
    resetData('private_space_with_guest').then((ids) => {
      cy.switchUser('guest')
      cy.visit(
        `/g/community/${ids.community}/space/${ids.private_space}/discussion/${ids.discussion}`,
      )
      cy.selectDropdownOption('Discussion Options', 'Report')
      submitReport('Spam', 'Invited Guest report')
    })
  })

  it('reports a discussion, protects reporter evidence, and resolves it with Hide', () => {
    resetData('space_with_discussion').then((ids) => {
      cy.switchUser('member')
      cy.visit(thread(ids))
      cy.get('button[aria-label="Discussion Options"]').click()
      cy.contains('[role="menuitem"]', /^Report$/).should('not.exist')
      cy.get('body').type('{esc}')
      cy.switchUser('secondMember')
      cy.visit(thread(ids))
      cy.selectDropdownOption('Discussion Options', 'Report')
      submitReport('Other', 'Needs moderator review')
      cy.switchUser('member')
      cy.visit(`/g/community/${ids.community}/moderation`)
      cy.contains('Only Community moderators can open this page.').should('be.visible')
      cy.switchUser('admin')
      reports(ids)
      cy.contains('button', /^Review$/).click()
      cy.contains('Needs moderator review').should('be.visible')
      cy.contains('button', 'Other · Second Member').should('be.visible')
      decision('Hide')
      cy.contains('No pending reports.').should('be.visible')
      cy.get('[role="dialog"]').should('not.exist')
      cy.get('[role="combobox"]').click()
      cy.contains('[role="option"]', 'Resolved').click()
      cy.contains('button', /^Review$/).click()
      cy.contains('Hide by').should('be.visible')
      cy.contains('Moderator reviewed the reports').should('be.visible')
    })
  })

  it('preserves reported reply evidence after edits and can uphold without hiding', () => {
    resetData('space_with_discussion').then((ids) => {
      cy.request('POST', '/api/v2/document/GP Comment', {
        reference_doctype: 'GP Discussion',
        reference_name: ids.discussion,
        content: '<p>Original reply evidence</p>',
      }).then(({ body }) => {
        const name = body.data.name
        cy.switchUser('secondMember')
        cy.visit(thread(ids))
        cy.get(`div[data-id="${name}"] button[aria-label="Comment Options"]`).click()
        cy.contains('[role="menuitem"]', /^Report$/).click()
        submitReport('Off-topic', 'Reply report')
        cy.switchUser('admin')
        cy.request('PUT', `/api/v2/document/GP Comment/${name}`, {
          content: '<p>Edited reply context</p>',
        })
        reports(ids)
        cy.contains('button', /^Review$/).click()
        cy.contains('Original reply evidence').should('be.visible')
        cy.contains('Edited reply context').should('be.visible')
        decision('Uphold')
        cy.contains('No pending reports.').should('be.visible')
        cy.visit(thread(ids))
        cy.contains('Edited reply context').should('be.visible')
      })
    })
  })

  it('rejects a decision on content edited while the moderator reviews it', () => {
    resetData('space_with_discussion').then((ids) => {
      cy.switchUser('secondMember')
      cy.request('POST', '/api/method/gameplan.reporting.submit', {
        doctype: 'GP Discussion',
        name: String(ids.discussion),
        reason: 'Spam',
      })
      cy.switchUser('admin')
      reports(ids)
      cy.contains('button', /^Review$/).click()
      cy.task('requestAsUser', {
        user: 'member@example.com',
        method: 'PUT',
        path: `/api/v2/document/GP Discussion/${ids.discussion}`,
        body: { content: '<p>Changed while reviewing</p>' },
      })
      decision('Delete Spam')
      cy.contains('This post changed.').should('be.visible')
      cy.contains('button', 'Refresh review').click()
      cy.contains('Changed while reviewing').should('be.visible')
      cy.get('[role="dialog"]').contains('button', 'Resolve review').click()
      cy.contains('No pending reports.').should('be.visible')
    })
  })
})
