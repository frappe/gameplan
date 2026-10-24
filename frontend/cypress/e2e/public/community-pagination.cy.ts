import { resetData } from '../../support/seed'

for (const destination of ['community', 'space', 'discussion']) {
  it(`opens a public ${destination} link when its Community is on a later page`, () => {
    resetData('public_space').then((ids) => {
      cy.clearCookies()
      const community = {
        name: ids.community,
        title: 'Open Source',
        visibility: 'Anonymous',
        members: [],
      }
      cy.intercept('GET', '**/gameplan.public_lists.communities*', (req) => {
        const start = Number(new URL(req.url).searchParams.get('start'))
        if (start === 0) {
          req.reply({
            data: Array.from({ length: 999 }, (_, index) => ({
              ...community,
              name: `earlier-community-${index}`,
              title: `Earlier Community ${index}`,
            })),
            has_next_page: true,
          })
        } else {
          expect(start).to.eq(999)
          req.alias = 'laterCommunities'
          req.reply({ data: [community], has_next_page: false })
        }
      })
      const paths = {
        community: `/g/community/${ids.community}/discussions`,
        space: `/g/community/${ids.community}/space/${ids.space}/discussions`,
        discussion: `/g/community/${ids.community}/space/${ids.space}/discussion/${ids.discussion}/${ids.discussion_slug}`,
      }
      const path = paths[destination as keyof typeof paths]
      cy.visit(path)
      cy.wait('@laterCommunities')
      cy.location('pathname').should('eq', path)
      cy.get('.gameplan-desktop-shell').contains('Open Source').should('be.visible')
      cy.contains('Welcome to Open Source').should('be.visible')
    })
  })
}
