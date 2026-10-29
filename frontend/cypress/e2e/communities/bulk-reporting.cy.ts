import { resetData, type SeedIds } from '../../support/seed'

function openReports(ids: SeedIds) {
  cy.switchUser('admin')
  cy.visit(`/g/community/${ids.community}/moderation`)
  cy.contains('button', /^Reports$/).click()
}
function seedReports(ids: SeedIds, count = 2) {
  const targets = [String(ids.discussion)]
  for (let i = 1; i < count; i++) {
    cy.request('POST', '/api/v2/document/GP Discussion', {
      title: `Bulk target ${i}`,
      project: ids.space,
      content: `<p>Body ${i}</p>`,
    }).then(({ body }) => targets.push(String(body.data.name)))
  }
  cy.switchUser('secondMember')
  cy.then(() => {
    for (const name of targets) {
      cy.request('POST', '/api/method/gameplan.reporting.submit', {
        doctype: 'GP Discussion',
        name,
        reason: 'Spam',
        note: 'Please review this post',
      })
    }
  })
  return cy.wrap(targets)
}
function confirm(decision: string) {
  cy.get('[role="dialog"] [role="combobox"]').click()
  cy.contains('[role="option"]', decision).click()
  cy.get('[role="dialog"] textarea').type('Reviewed these reports together')
  cy.get('[role="dialog"]')
    .contains('button', /^Resolve \d+ reviews$/)
    .click()
}

describe('Bulk report review', () => {
  it('previews reports, opens full evidence, and removes spam with a shared note', () => {
    resetData('space_with_discussion').then((ids) => {
      seedReports(ids).then((targets) => {
        openReports(ids)
        cy.contains('button', 'Select this page').click()
        cy.contains('2 of 50 selected').should('be.visible')
        cy.contains('button', 'Review selected').click()
        cy.get('[role="dialog"]').contains('Spam: 1').should('be.visible')
        cy.get('[role="dialog"]').contains('Seed content').should('be.visible')
        cy.get('[role="dialog"]').contains('button', 'Full review').first().click()
        cy.contains('Reported versions').should('be.visible')
        cy.contains('Please review this post').should('be.visible')
        cy.get('body').type('{esc}')
        cy.contains('button', 'Review selected').click()
        confirm('Delete Spam')
        cy.contains('2 of 2 processed · 2 resolved.').should('be.visible')
        cy.get('[role="dialog"]').contains('button', 'Done').click()
        cy.contains('No pending reports.').should('be.visible')
        for (const name of targets) {
          cy.request(`/api/v2/document/GP Discussion/${name}`)
            .its('body.data.spam_removed_at')
            .should('be.ok')
        }
        cy.task<{ message: { items: { decision_note: string }[] } }>('requestAsUser', {
          user: 'Administrator',
          path: '/api/method/gameplan.reporting.queue',
          body: { community: ids.community, status: 'Resolved' },
        }).then((body) => {
          expect(body.message.items).to.have.length(2)
          body.message.items.forEach((item: { decision_note: string }) => {
            expect(item.decision_note).to.eq('Reviewed these reports together')
          })
        })
      })
    })
  })

  it('keeps successful decisions when other posts change or reviews are resolved', () => {
    resetData('space_with_discussion').then((ids) => {
      seedReports(ids, 3).then((targets) => {
        openReports(ids)
        cy.intercept('POST', '**/gameplan.reporting_bulk.preview').as('preview')
        cy.contains('button', 'Select this page').click()
        cy.contains('button', 'Review selected').click()
        cy.wait('@preview').then(({ response }) => {
          const items = response!.body.message
          const resolved = items.find(
            (item: { reference_name: string }) => item.reference_name === targets[2],
          )
          cy.task('requestAsUser', {
            user: 'Administrator',
            method: 'PUT',
            path: `/api/v2/document/GP Discussion/${targets[1]}`,
            body: { content: '<p>Edited after preview</p>' },
          })
          cy.task('requestAsUser', {
            user: 'Administrator',
            path: '/api/method/gameplan.reporting.resolve',
            body: {
              community: ids.community,
              review: resolved.review,
              decision: 'Dismiss',
              note: 'Another decision',
              expected_version: resolved.version,
            },
          })
        })
        confirm('Hide')
        cy.contains('3 of 3 processed · 1 resolved.').should('be.visible')
        cy.contains('This post changed.').should('be.visible')
        cy.contains('This review was already resolved.').should('be.visible')
        cy.get('[role="dialog"]').contains('button', 'Done').click()
        cy.contains('1 of 50 selected').should('not.exist')
        cy.request(`/api/v2/document/GP Discussion/${targets[0]}`)
          .its('body.data.hidden_at')
          .should('be.ok')
        cy.request(`/api/v2/document/GP Discussion/${targets[1]}`)
          .its('body.data.hidden_at')
          .should('not.be.ok')
        cy.contains('button', 'Select this page').click()
        cy.contains('button', 'Review selected').click()
        cy.contains('Edited after preview').should('be.visible')
        confirm('Uphold')
        cy.contains('1 of 1 processed · 1 resolved.').should('be.visible')
      })
    })
  })

  it('keeps selections across pages, caps them at 50, and clears them on status changes', () => {
    resetData('space_with_discussion').then((ids) => {
      cy.intercept('POST', '**/gameplan.reporting.queue', (req) => {
        const start = Number(req.body.start || 0)
        req.reply({
          message: {
            items: Array.from({ length: 40 }, (_, i) => ({
              name: `review-${start + i}`,
              reference_doctype: 'GP Discussion',
              reference_name: String(start + i),
              creation: '2026-10-23 10:00:00',
            })),
            has_more: start === 0,
          },
        })
      })
      openReports(ids)
      cy.contains('button', 'Select this page').click()
      cy.contains('40 of 50 selected').should('be.visible')
      cy.contains('button', /^Next$/).click()
      cy.contains('button', 'Select this page').should('be.disabled')
      for (let i = 0; i < 10; i++) cy.get('input[aria-label^="Select discussion"]').eq(i).check()
      cy.contains('50 of 50 selected').scrollIntoView().should('be.visible')
      cy.get('input[aria-label^="Select discussion"]').eq(10).should('be.disabled')
      cy.contains('button', /^Previous$/).click()
      cy.get('input[aria-label^="Select discussion"]:checked').should('have.length', 40)
      cy.contains('button', 'Clear selection').click()
      cy.contains('0 of 50 selected').should('be.visible')
      cy.contains('button', 'Select this page').click()
      cy.get('[role="combobox"]').click()
      cy.contains('[role="option"]', 'Resolved').click()
      cy.get('input[aria-label^="Select discussion"]').should('not.exist')
      cy.get('[role="combobox"]').click()
      cy.contains('[role="option"]', 'Pending').click()
      cy.contains('0 of 50 selected').should('be.visible')
    })
  })
})
