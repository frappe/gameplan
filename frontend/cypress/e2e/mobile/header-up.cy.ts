// On a phone, the header button of a Space or a discussion goes up one level. The back
// gesture still follows history, and going up must not leave a way back to the page left.
import type { App } from 'vue'
import { resetData } from '../../support/seed'

type VueAppElement = Element & { __vue_app__: App }

describe('Mobile header goes up', () => {
  const pathIs = (path: string) => cy.location('pathname').should('equal', path)
  const tapBack = () => cy.iconButton('Back').click()

  beforeEach(() => {
    cy.viewport('iphone-6')
  })

  describe('with a discussion in a Space', () => {
    let communityPath: string
    let spacePath: string
    let discussionPath: string

    beforeEach(() => {
      resetData('space_with_discussion').then(
        ({ community, space, discussion, discussion_slug }) => {
          communityPath = `/g/community/${community}/discussions`
          spacePath = `/g/community/${community}/space/${space}/discussions`
          discussionPath = `/g/community/${community}/space/${space}/discussion/${discussion}/${discussion_slug}`
        },
      )
      cy.loginAs('member')
    })

    it('climbs back down the way the user came without a loop', () => {
      cy.visit('/g/home')
      cy.contains('button', 'Acme').click()
      pathIs(communityPath)
      cy.contains('button', 'All Discussions').click()
      cy.scope('dialog').button('Engineering').click()
      pathIs(spacePath)
      cy.contains('a:visible', 'Welcome thread').click()
      pathIs(discussionPath)

      tapBack()
      pathIs(spacePath)
      tapBack()
      pathIs(communityPath)

      // Neither the Space nor the discussion is left behind this entry.
      cy.go('back')
      pathIs('/g/home')
    })

    it('goes to the Space from a discussion opened elsewhere', () => {
      cy.visit('/g/home')
      cy.contains('button', 'Acme').click()
      pathIs(communityPath)
      cy.contains('a:visible', 'Welcome thread').click()
      pathIs(discussionPath)

      tapBack()
      pathIs(spacePath)

      // The gesture returns to where the user was, not to the discussion.
      cy.go('back')
      pathIs(communityPath)
    })

    it('goes up from a link opened directly', () => {
      cy.visit(discussionPath)
      cy.contains('Seed content').should('be.visible')
      tapBack()
      pathIs(spacePath)
      tapBack()
      pathIs(communityPath)
    })

    it('reaches the Space when the entry before the discussion has changed', () => {
      cy.visit(spacePath)
      cy.contains('a:visible', 'Welcome thread').click()
      pathIs(discussionPath)
      cy.contains('Seed content').should('be.visible')
      cy.go('back')
      pathIs(spacePath)

      // Going up replaces the Space's entry, but the discussion still records it as previous.
      tapBack()
      pathIs(communityPath)
      cy.go('forward')
      pathIs(discussionPath)
      cy.contains('Seed content').should('be.visible')

      tapBack()
      pathIs(spacePath)
    })
  })

  it('goes to the current Space of a discussion moved elsewhere', () => {
    resetData('space_with_discussion').then(({ community, space, general_space, discussion }) => {
      cy.loginAs('member')
      cy.visit(`/g/community/${community}/space/${general_space}/discussion/${discussion}`)
      cy.contains('Seed content').should('be.visible')
      tapBack()
      pathIs(`/g/community/${community}/space/${space}/discussions`)
    })
  })

  it('goes to the Space in the URL when the discussion cannot be opened', () => {
    resetData('private_space_with_guest').then(({ community, space, discussion }) => {
      const spacePath = `/community/${community}/space/${space}`
      cy.loginAs('secondMember')
      cy.visit(`/g${spacePath}/discussions`)
      cy.iconButton('Back').should('be.visible')

      // An in-app link: a cold load of this URL stops at the router's not found page.
      cy.window().then((win) => {
        const app = (win.document.querySelector('#app') as VueAppElement).__vue_app__
        app.config.globalProperties.$router.push(
          `${spacePath}/discussion/${discussion}/secret-thread`,
        )
      })
      cy.contains('Discussion not found').should('be.visible')
      pathIs(`/g${spacePath}/discussion/${discussion}/secret-thread`)

      tapBack()
      pathIs(`/g${spacePath}/discussions`)
    })
  })
})
