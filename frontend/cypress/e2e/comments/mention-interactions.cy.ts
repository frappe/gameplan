import { resetData } from '../../support/seed'

const mention = '[data-type="mention"][data-id="member2@example.com"]'
const everyone = '[data-type="mention"][data-id="_everyone_"]'
const content = `<p>Hello <span class="mention" data-type="mention" data-id="member2@example.com" data-label="Second Member">@Second Member</span> and <span class="mention" data-type="mention" data-id="_everyone_" data-label="Everyone">@Everyone</span></p>`

describe('Mention interactions', () => {
  let discussionUrl: string
  let commentSelector: string
  let profile: string

  beforeEach(() => {
    resetData('space_with_discussion').then(({ community, space, discussion }) => {
      discussionUrl = `/g/community/${community}/space/${space}/discussion/${discussion}`
      cy.loginAs('member')
      cy.request('GET', '/api/v2/method/gameplan.api.get_user_info').then(({ body }) => {
        profile = body.data.find(
          (user: { name: string }) => user.name === 'member2@example.com',
        ).user_profile
      })
      cy.request('PUT', `/api/v2/document/GP%20Discussion/${discussion}`, { content })
      cy.request('POST', '/api/v2/document/GP%20Comment', {
        reference_doctype: 'GP Discussion',
        reference_name: discussion,
        content,
      }).then(({ body }) => {
        commentSelector = `div[data-id="${body.data.name}"]`
      })
    })
  })

  for (const surface of ['post', 'comment']) {
    it(`shows the mentioned user's card and opens their profile from a ${surface}`, () => {
      cy.visit(discussionUrl)
      const scope = surface === 'post' ? '.discussion-container' : commentSelector

      cy.get(`${scope} ${everyone}`).click()
      cy.location('pathname').should('include', discussionUrl)

      cy.get(`${scope} ${mention} button`).trigger('pointerenter', {
        eventConstructor: 'PointerEvent',
        pointerType: 'mouse',
      })
      cy.contains('in the last 3 months').should('be.visible')
      cy.contains('in the last 3 months').parent().should('contain.text', 'Second Member')

      cy.get(`${scope} ${mention}`).contains('button', '@Second Member').click()
      cy.location('pathname').should('eq', `/g/people/${profile}`)
      cy.contains('Second Member').should('be.visible')
    })
  }
})
