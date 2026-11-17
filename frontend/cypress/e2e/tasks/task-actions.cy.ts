import { resetData } from '../../support/seed'

// One linear flow: every step edits the task created in the step before it, so
// splitting these into separate `it()`s would only mean re-creating the task.
describe('Task actions', () => {
  let community: string
  let space: string

  beforeEach(() => {
    resetData('onboarded').then((ids) => {
      community = String(ids.community)
      space = String(ids.space)
    })
    cy.loginAs('member')
  })

  it("sets a task's title, assignee, due date, and status", () => {
    // A space has no task list to create tasks from any more, so the task is created
    // through the API and opened at its own URL.
    cy.request('POST', '/api/v2/document/GP%20Task', {
      title: 'First Task',
      description: '<p>This is the description of the first task</p>',
      project: space,
    }).then(({ body }) => {
      cy.intercept('POST', '/api/v2/document/GP%20Task/*/method/track_visit').as('trackVisit')
      cy.visit(`/g/community/${community}/space/${space}/tasks/${body.data.name}`)
    })
    cy.wait('@trackVisit')

    // Every edit below saves through the same endpoint, so one alias covers them all.
    // Separate aliases on an identical matcher would all capture the same requests and
    // each wait would read whichever response arrived first.
    cy.intercept('PUT', '/api/v2/document/GP%20Task/*').as('saveTask')

    // rename it — the title input saves on blur
    cy.get('input[placeholder="Title"]').click().type('{selectall}Edited Task Title')
    cy.get('input[placeholder="Title"]').blur()
    cy.wait('@saveTask').its('response.body.data.title').should('eq', 'Edited Task Title')

    // assign it to the community's other member
    cy.selectCombobox('Assign a user', 'Second Member')
    cy.wait('@saveTask').its('response.body.data.assigned_to').should('eq', 'member2@example.com')

    // set a due date — Enter commits the typed date and closes the calendar, which
    // would otherwise stay open and overlay the Status control below it.
    const dueDate = new Date().toISOString().split('T')[0]
    cy.get('input[placeholder="Due date"]:visible')
      .click()
      .clear()
      .type(`${dueDate}{enter}`, { force: true })
    cy.wait('@saveTask').its('response.body.data.due_date').should('eq', dueDate)

    // mark it done
    cy.contains('div', 'Status').next('div').find('[role="combobox"]').click()
    cy.get('[role="option"]:contains("Done"):visible').click()
    cy.wait('@saveTask').its('response.body.data.status').should('eq', 'Done')
  })
})
