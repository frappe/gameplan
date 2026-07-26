import { defineConfig } from 'cypress'

interface RequestAsUserOptions {
  user: string
  password?: string
  path: string
  method?: string
  body?: unknown
}

interface RealtimePreflightOptions {
  user?: string
  password?: string
}

const DEMO_SITE = 'gameplan-demo.test'

function originAtPort(baseUrl: string, port: number) {
  const url = new URL(baseUrl)
  url.port = String(port)
  return url.origin
}

async function login(baseUrl: string, user: string, password: string) {
  const response = await fetch(`${baseUrl}/api/method/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ usr: user, pwd: password }),
  })
  if (!response.ok) throw new Error(`Could not log in as ${user}: ${response.status}`)

  return response.headers
    .getSetCookie()
    .map((cookie) => cookie.split(';')[0])
    .join('; ')
}

function serverStartCommand(port: number) {
  return `bench --site ${DEMO_SITE} serve --port ${port}`
}

async function assertDemoSite(baseUrl: string, port: number, purpose: string) {
  const startCommand = serverStartCommand(port)
  let response: Response
  try {
    response = await fetch(`${baseUrl}/api/method/gameplan.www.g.get_context_for_dev`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    })
  } catch (error) {
    throw new Error(
      `${purpose} on :${port} is not responding. Start it with: ${startCommand}. ` +
        `Run it from the frappe-bench directory. Original error: ${String(error)}`,
    )
  }

  if (!response.ok) {
    throw new Error(
      `${purpose} on :${port} did not resolve to ${DEMO_SITE} (${response.status}). ` +
        `Start it from the frappe-bench directory with: ${startCommand}`,
    )
  }

  const payload = (await response.json()) as { message?: { site_name?: string } }
  if (payload.message?.site_name !== DEMO_SITE) {
    throw new Error(
      `${purpose} on :${port} resolved to ${payload.message?.site_name ?? 'an unknown site'}, ` +
        `not ${DEMO_SITE}. Start it from the frappe-bench directory with: ${startCommand}`,
    )
  }
}

async function assertUserResolves(baseUrl: string, port: number, user: string, password: string) {
  const purpose = port === 8000 ? 'Realtime authentication target' : 'Cypress web server'
  const startCommand = serverStartCommand(port)
  try {
    const cookie = await login(baseUrl, user, password)
    const response = await fetch(`${baseUrl}/api/method/frappe.auth.get_logged_user`, {
      headers: { Cookie: cookie },
    })
    const payload = (await response.json()) as { message?: string }
    if (!response.ok || payload.message !== user) {
      throw new Error(
        `resolved seeded persona ${user} as ${payload.message ?? 'unknown'} (${response.status})`,
      )
    }
  } catch (error) {
    throw new Error(
      `${purpose} on :${port} could not authenticate and resolve seeded persona ${user}. ` +
        `Start it from the frappe-bench directory with: ${startCommand}. ` +
        `Original error: ${String(error)}`,
    )
  }
}

async function assertSocketServer(baseUrl: string) {
  const socketUrl = new URL(baseUrl)
  socketUrl.port = '9000'
  socketUrl.pathname = '/socket.io/'
  socketUrl.search = `EIO=4&transport=polling&t=${Date.now()}`
  const startCommand = 'bench socketio'

  let response: Response
  try {
    response = await fetch(socketUrl, { headers: { Origin: new URL(baseUrl).origin } })
  } catch (error) {
    throw new Error(
      `Socket.IO server on :9000 is not listening. Start it with: ${startCommand}. ` +
        `Run it from the frappe-bench directory. Original error: ${String(error)}`,
    )
  }

  const body = await response.text()
  if (!response.ok || !body.startsWith('0{')) {
    throw new Error(
      `Socket.IO server on :9000 failed its polling handshake (${response.status}). ` +
        `Start it from the frappe-bench directory with: ${startCommand}`,
    )
  }
}

/**
 * Prove the three-process local realtime setup by behavior, not process names.
 *
 * The optional user check is run after the scenario seed. Each port gets a newly
 * minted session and resolves it immediately in this same task, so an expired sid
 * cannot be misreported as the wrong site.
 */
async function realtimePreflight(
  baseUrl: string | null,
  { user, password = 'admin' }: RealtimePreflightOptions = {},
) {
  if (!baseUrl) throw new Error('Cypress baseUrl is required for the realtime preflight')
  if (new URL(baseUrl).port !== '8002') {
    throw new Error(`Realtime E2E must run against ${DEMO_SITE}:8002, received ${baseUrl}`)
  }

  const webServer = originAtPort(baseUrl, 8002)
  const authServer = originAtPort(baseUrl, 8000)
  await assertDemoSite(webServer, 8002, 'Cypress web server')
  await assertDemoSite(authServer, 8000, 'Realtime authentication target')
  await assertSocketServer(baseUrl)

  if (user) {
    await assertUserResolves(webServer, 8002, user, password)
    await assertUserResolves(authServer, 8000, user, password)
  }

  return null
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
  if (!baseUrl) throw new Error('Cypress baseUrl is required for requestAsUser')
  const cookie = await login(baseUrl, user, password)

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
      on('task', {
        realtimePreflight: (options) => realtimePreflight(config.baseUrl, options ?? undefined),
        requestAsUser: (options) => requestAsUser(config.baseUrl, options),
      })
      return config
    },
  },
  retries: {
    runMode: 2,
    openMode: 0,
  },
})
