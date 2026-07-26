import { defineConfig } from 'cypress'

interface RequestAsUserOptions {
  user: string
  password?: string
  path: string
  method?: string
  body?: unknown
}

/**
 * Call the API as a second user, in a session of its own.
 *
 * This runs in Node rather than through `cy.request` on purpose: `cy.request`
 * shares the browser's cookie jar, so it always acts as whoever the open page is
 * logged in as — it cannot represent a *different* person while that page stays
 * loaded. A spec that needs "someone else changed this while I was looking at it"
 * needs a session the browser knows nothing about.
 *
 * The session never renders a page, so it has no CSRF token and Frappe skips the
 * CSRF check (`frappe/auth.py::validate_csrf_token`).
 */
async function requestAsUser(
  baseUrl: string | null,
  { user, password = 'admin', path, method = 'POST', body }: RequestAsUserOptions,
) {
  const login = await fetch(`${baseUrl}/api/method/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ usr: user, pwd: password }),
  })
  if (!login.ok) throw new Error(`Could not log in as ${user}: ${login.status}`)

  const cookie = login.headers
    .getSetCookie()
    .map((c) => c.split(';')[0])
    .join('; ')

  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', Cookie: cookie },
    body: method === 'GET' ? undefined : JSON.stringify(body ?? {}),
  })
  const text = await response.text()
  if (!response.ok)
    throw new Error(`${method} ${path} as ${user} failed (${response.status}): ${text}`)

  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

export default defineConfig({
  // JUnit XML per spec; CI parses these to post a results comment on the PR
  // (replaces Cypress Cloud recording). [hash] keeps one file per spec.
  reporter: 'mocha-junit-reporter',
  reporterOptions: {
    mochaFile: 'cypress/results/results-[hash].xml',
    toConsole: true,
  },
  video: true,
  e2e: {
    baseUrl: 'http://gameplan-demo.test:8000',
    supportFile: 'cypress/support/e2e.ts',
    specPattern: 'cypress/e2e/**/*.{js,jsx,ts,tsx}',
    setupNodeEvents(on, config) {
      on('task', { requestAsUser: (options) => requestAsUser(config.baseUrl, options) })
      return config
    },
  },
  retries: {
    runMode: 2,
    openMode: 0,
  },
})
