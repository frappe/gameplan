// Frappe answers 508 when a request loses a database lock race. On a local SQLite site a
// login can lose one to requests still finishing from the previous test, so it tries again.
// CI runs MariaDB, where this does not happen.
const ATTEMPTS = 4

export function requestLogin(usr: string, pwd: string, attempt = 1): Cypress.Chainable<unknown> {
  return cy
    .request({
      url: '/api/method/login',
      method: 'POST',
      body: { usr, pwd },
      failOnStatusCode: false,
    })
    .then((response) => {
      if (response.status === 508 && attempt < ATTEMPTS) {
        cy.wait(250 * attempt, { log: false })
        return requestLogin(usr, pwd, attempt + 1)
      }
      expect(response.status, `log in as ${usr}`).to.eq(200)
    })
}
