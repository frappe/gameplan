import { resetData, type SeedIds } from '../../support/seed'

describe('Public access regression checks', () => {
  let ids: SeedIds

  beforeEach(() => {
    resetData('public_space').then((seeded) => (ids = seeded))
    cy.viewport(390, 844)
  })

  function openVisibility() {
    cy.request('POST', `/api/v2/document/GP Team/${ids.community}/method/set_visibility`, {
      visibility: 'General',
    })
    cy.visit('/g/settings/communities')
    cy.iconButton('Open Source Community Options').click()
    cy.contains('[role="menuitem"]', 'Change visibility').click()
    cy.contains('[role="dialog"]', 'Visibility of Open Source').should('be.visible')
  }

  it('ignores an earlier preview while the public exposure preview is pending', () => {
    openVisibility()
    cy.intercept('POST', '**/method/get_visibility_change_impact', (req) => {
      const anonymous = req.body.visibility === 'Anonymous'
      req.alias = anonymous ? 'publicImpact' : 'oldImpact'
      req.reply({
        delay: anonymous ? 1200 : 200,
        body: { data: { discussions_made_public: anonymous ? 25 : 0 } },
      })
    })
    cy.contains('[role="radio"]', 'Member Access').click()
    cy.contains('[role="radio"]', 'Anonymous').click()
    cy.wait('@oldImpact')
    cy.contains('button', 'Change visibility').should('be.disabled')
    cy.wait('@publicImpact')
    cy.contains('25 discussions become readable by anyone on the web').should('be.visible')
    cy.contains('button', 'Change visibility').should('not.be.disabled')
  })

  it('requires a successful preview and lets the admin retry', () => {
    openVisibility()
    cy.intercept('POST', '**/method/get_visibility_change_impact', {
      statusCode: 500,
      body: { exception: 'Could not preview visibility' },
    }).as('failedImpact')
    cy.contains('[role="radio"]', 'Anonymous').focus().type(' ')
    cy.wait('@failedImpact')
    cy.contains('button', 'Change visibility').should('be.disabled')
    cy.intercept('POST', '**/method/get_visibility_change_impact', {
      body: { data: { discussions_made_public: 1 } },
    }).as('retryImpact')
    cy.contains('[role="radio"]', 'Anonymous').click()
    cy.wait('@retryImpact')
    cy.contains('1 discussion becomes readable by anyone on the web').should('be.visible')
    cy.contains('button', 'Change visibility').should('not.be.disabled')
  })

  it('warns that publishing a community exposes its existing Anonymous spaces', () => {
    openVisibility()
    cy.contains('[role="radio"]', 'Anonymous').click()
    cy.contains('1 discussion becomes readable by anyone on the web').should('be.visible')
    cy.contains('No space inside becomes public from this').should('not.exist')
  })

  it('shows matching counts and separate Anonymous filters for communities and spaces', () => {
    cy.visit('/g/settings/communities')
    cy.contains('button[role="combobox"]', 'All (1)').click()
    cy.contains('[role="option"]', 'General (0)').should('be.visible')
    cy.contains('[role="option"]', 'Anonymous (1)').click()
    cy.iconButton('Open Source Community Options').should('be.visible')
    cy.visit(`/g/settings/communities/${ids.community}/spaces`)
    cy.contains('button[role="combobox"]', 'All (3)').click()
    cy.contains('[role="option"]', 'General (1)').should('be.visible')
    cy.contains('[role="option"]', 'Member Access (1)').should('be.visible')
    cy.contains('[role="option"]', 'Anonymous (1)').click()
    cy.get('input[aria-label="Space title"]')
      .should('have.length', 1)
      .and('have.value', 'Announcements')
  })

  it('loads more than 100 author profiles and retries a failed batch', () => {
    let failed = false
    const described = new Set<string>()
    cy.intercept('**/gameplan.public_lists.comments*', (req) => {
      req.continue((res) => {
        const comment = res.body.data[0]
        res.body.data = Array.from({ length: 101 }, (_, i) => ({
          ...comment,
          name: `profile-comment-${i}`,
          owner: `profile-author-${i}`,
          content: `<p>Profile test reply ${i}</p>`,
        }))
        res.body.has_next_page = false
      })
    })
    cy.intercept('POST', '**/gameplan.api.get_public_user_info', (req) => {
      const handles: string[] = req.body.handles
      expect(handles.length).to.be.at.most(100)
      if (!failed) {
        failed = true
        req.reply({ statusCode: 503, body: { exception: 'Temporary profile failure' } })
        return
      }
      handles.forEach((handle) => described.add(handle))
      req.reply({
        body: { message: handles.map((handle) => ({ handle, full_name: `Name ${handle}` })) },
      })
    })
    cy.clearCookies()
    cy.visit(`/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}`)
    cy.contains('Name profile-author-100', { timeout: 15000 }).should('exist')
    cy.wrap(null).should(() => {
      expect(failed).to.eq(true)
      for (let i = 0; i < 101; i++) expect(described.has(`profile-author-${i}`)).to.eq(true)
    })
  })
})
