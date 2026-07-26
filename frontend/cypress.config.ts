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

interface RealtimePreflightResult {
  available: boolean
  reason?: string
}

const REALTIME_AUTH_PORT = Number(process.env.GAMEPLAN_REALTIME_AUTH_PORT || 8000)
const SOCKET_PORT = Number(process.env.GAMEPLAN_SOCKET_PORT || 9000)

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

function serverStartCommand(site: string, port: number) {
  return `bench --site ${site} serve --port ${port}`
}

async function assertDemoSite(baseUrl: string, port: number, purpose: string, expectedSite: string) {
  const startCommand = serverStartCommand(expectedSite, port)
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

  const text = await response.text()
  let payload: {
    message?: { site_name?: string }
    exception?: string
    exc_type?: string
    _server_messages?: string
  } = {}
  try {
    payload = JSON.parse(text)
  } catch {
    // The status-specific diagnostic below still names an unavailable probe.
  }

  if (!response.ok) {
    const failure = [payload.exception, payload.exc_type, payload._server_messages, text]
      .filter(Boolean)
      .join(' ')
    if (failure.includes('This method is only meant for developer mode')) {
      throw new Error(
        `${purpose} on :${port} resolves to a Frappe site, but developer_mode is disabled. ` +
          `Enable developer_mode for the realtime site probe, then restart the server.`,
      )
    }
    if (
      response.status === 404 ||
      failure.includes('Failed to get method') ||
      failure.includes('MethodNotFound')
    ) {
      throw new Error(
        `${purpose} on :${port} is responding, but the Gameplan site probe endpoint is disabled ` +
          `or unavailable (${response.status}). Confirm Gameplan is installed and ` +
          `gameplan.www.g.get_context_for_dev is enabled.`,
      )
    }
    throw new Error(
      `${purpose} on :${port} failed the Gameplan site probe (${response.status}). ` +
        `Start ${expectedSite} from the frappe-bench directory with: ${startCommand}`,
    )
  }

  if (payload.message?.site_name !== expectedSite) {
    throw new Error(
      `${purpose} on :${port} resolved to ${payload.message?.site_name ?? 'an unknown site'}, ` +
        `not ${expectedSite}. Start it from the frappe-bench directory with: ${startCommand}`,
    )
  }
}

async function assertUserResolves(
  baseUrl: string,
  port: number,
  purpose: string,
  expectedSite: string,
  user: string,
  password: string,
) {
  const startCommand = serverStartCommand(expectedSite, port)
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
  socketUrl.port = String(SOCKET_PORT)
  socketUrl.pathname = '/socket.io/'
  socketUrl.search = `EIO=4&transport=polling&t=${Date.now()}`
  const startCommand = 'bench socketio'

  let response: Response
  try {
    response = await fetch(socketUrl, { headers: { Origin: new URL(baseUrl).origin } })
  } catch (error) {
    throw new Error(
      `Socket.IO server on :${SOCKET_PORT} is not listening. Start it with: ${startCommand}. ` +
        `Run it from the frappe-bench directory. Original error: ${String(error)}`,
    )
  }

  const body = await response.text()
  if (!response.ok || !body.startsWith('0{')) {
    throw new Error(
      `Socket.IO server on :${SOCKET_PORT} failed its polling handshake (${response.status}). ` +
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
): Promise<RealtimePreflightResult> {
  if (!baseUrl) throw new Error('Cypress baseUrl is required for the realtime preflight')
  if (process.env.SKIP_REALTIME_E2E) {
    const reason = `Realtime E2E skipped: ${process.env.SKIP_REALTIME_E2E}`
    console.warn(reason)
    return { available: false, reason }
  }

  const configuredUrl = new URL(baseUrl)
  const expectedSite = configuredUrl.hostname
  const webPort = Number(configuredUrl.port || (configuredUrl.protocol === 'https:' ? 443 : 80))
  const webServer = configuredUrl.origin
  const authServer = originAtPort(baseUrl, REALTIME_AUTH_PORT)
  await assertDemoSite(webServer, webPort, 'Cypress web server', expectedSite)
  await assertDemoSite(
    authServer,
    REALTIME_AUTH_PORT,
    'Realtime authentication target',
    expectedSite,
  )
  await assertSocketServer(baseUrl)

  if (user) {
    await assertUserResolves(
      webServer,
      webPort,
      'Cypress web server',
      expectedSite,
      user,
      password,
    )
    await assertUserResolves(
      authServer,
      REALTIME_AUTH_PORT,
      'Realtime authentication target',
      expectedSite,
      user,
      password,
    )
  }

  return { available: true }
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
    baseUrl: 'http://gameplan-demo.test:8002',
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
