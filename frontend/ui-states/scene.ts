import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { dirname, resolve } from 'node:path'
import { request, type APIRequestContext, type Browser, type BrowserContext, type Page, type Route } from '@playwright/test'

const VIEWPORT = { width: 1440, height: 900 }
/** Enough for frappe-ui transitions to finish. */
const SETTLE_MS = 450
const ADMIN_PASSWORD = process.env.UI_STATES_ADMIN_PASSWORD ?? 'admin'
const PILOT = process.env.UI_STATES_PILOT ?? resolve(homedir(), 'pilot/bin/pilot')
const BENCH = process.env.UI_STATES_BENCH

/** The bare seed scenarios `gameplan.ui_test_helpers.reset` builds, for states the demo world cannot show. */
export type Scenario =
  | 'onboarded'
  | 'space_with_discussion'
  | 'private_space_with_guest'
  | 'search_page'
  | 'two_communities'
  | 'unread_discussion'

/** The ids a scenario returns, as `reset` names them. */
export interface SeedIds {
  community?: string
  space?: string
  general_space?: string
  second_space?: string
  private_space?: string
  discussion?: string
  discussion_slug?: string
  public_discussion?: string
  communities?: string[]
  spaces?: string[]
}

export interface Person {
  email: string
  fullName: string
  /** Demo people have none; the dev user switcher signs them in. */
  password?: string
}

/**
 * The people of Gameplan's demo world, Moonhollow Studios
 * (`gameplan/demo/world.md`). Maya is the demo's own viewer: the seeder gives
 * her drafts, bookmarks, unread threads and notifications.
 */
export const people = {
  /** Producer and Gameplan Admin. The signed-in person in every demo path. */
  actor: { email: 'maya@moonhollow.studio', fullName: 'Maya Iyer' },
  /** Lead engineer, a Gameplan Member: replies, reacts, mentions Maya. */
  peer: { email: 'priya@moonhollow.studio', fullName: 'Priya Sharma' },
  /** Engineering intern, a Gameplan Member with no admin rights, for member-only views. */
  member: { email: 'felix@moonhollow.studio', fullName: 'Felix Novak' },
  /** Frappe's Administrator. */
  admin: { email: 'Administrator', fullName: 'Administrator', password: ADMIN_PASSWORD },
} satisfies Record<string, Person>

/** The demo's communities, by name. */
export const communities = {
  commonRoom: 'common-room',
  studio: 'studio',
  marketing: 'marketing-hub',
  bluebird: 'project-bluebird',
} as const

/**
 * The personas a bare `reset` scenario provisions, renamed so a screenshot
 * still reads like Moonhollow. They exist only after `scene.seed()`.
 */
export const testPeople = {
  /** A Gameplan Member in every scenario's community. `seed` signs the page in as her. */
  member: { email: 'member@example.com', fullName: 'Maya Iyer', password: 'admin' },
  /** A second Gameplan Member in every scenario's community. */
  member2: { email: 'member2@example.com', fullName: 'Felix Novak', password: 'admin' },
  /** A Gameplan Guest, with access only where a scenario grants it. */
  guest: { email: 'guest@example.com', fullName: 'Chloe Kim', password: 'admin' },
  /** A Gameplan Member outside every community. */
  outsider: { email: 'outsider@example.com', fullName: 'Dev Patel', password: 'admin' },
} satisfies Record<string, Person>

export type People = typeof people

/**
 * A request hold: traffic matching the pattern waits until the hold ends.
 * `abort` fails the held requests and every later match, since the transport
 * retries server errors, until `release` lets traffic through again.
 */
export interface Hold {
  release(): Promise<void>
  abort(status?: number): Promise<void>
}

export interface Space {
  name: string
  title: string
}

/**
 * One browser session in one capture path, signed in as Maya in a freshly
 * loaded demo world.
 *
 * Loading the demo replaces every Gameplan row on the site, so scenes do not
 * get a workspace of their own: each scene reloads the whole world. That is
 * safe only because a run captures one flow at a time, with one worker, and
 * its paths run one after another.
 */
export interface Scene {
  page: Page
  context: BrowserContext
  /** A session of its own for the signed-in person, separate from `page`. */
  api: APIRequestContext
  /** An Administrator session, for seeding what the actor cannot. */
  admin: APIRequestContext
  baseURL: string
  people: People
  /** Who `page` and `api` are signed in as. */
  actor: Person
  /** What the last `seed` returned; empty in the demo world. */
  ids: SeedIds
  /**
   * Replaces the demo with a bare test scenario, for states the demo cannot
   * show. With no scenario the site has no communities at all. Signs `page`
   * and `api` in as `testPeople.member`.
   */
  seed(scenario?: Scenario): Promise<SeedIds>
  /** Signs `page` and `api` in as someone else. Reload or navigate afterwards. */
  signIn(person: Person): Promise<void>
  /** A new, empty public space in a community, named after the flow and created on first use. */
  space(community?: string): Promise<Space>
  /** The first document's name matching the filters, or throws. */
  find(doctype: string, filters: Record<string, unknown>): Promise<string>
  /** Calls a whitelisted method with POST and returns its `message`. */
  call<T = unknown>(api: APIRequestContext, method: string, args?: Record<string, unknown>): Promise<T>
  /** Runs a whitelisted document method with POST and returns its result. */
  method<T = unknown>(
    api: APIRequestContext,
    doctype: string,
    name: string,
    method: string,
    args?: Record<string, unknown>,
  ): Promise<T>
  /** Inserts a document and returns it. */
  insert<T = Record<string, unknown>>(api: APIRequestContext, doctype: string, doc: Record<string, unknown>): Promise<T>
  /** Opens a path under `/g`. */
  goto(path: string): Promise<void>
  /** Holds requests whose URL matches until released or aborted. */
  hold(url: string | RegExp): Promise<Hold>
  /** Waits for transitions to finish. */
  settle(ms?: number): Promise<void>
  /** A separate session signed in as another person. */
  as(person: Person): Promise<APIRequestContext>
  close(): Promise<void>
}

export async function openScene(browser: Browser, baseURL: string, label: string): Promise<Scene> {
  loadDemo(baseURL)
  const admin = await request.newContext({ baseURL })
  await login(admin)

  const context = await browser.newContext({ baseURL, viewport: VIEWPORT, colorScheme: 'light' })
  await signInAs(context.request, people.actor)
  const page = await context.newPage()
  // A session of its own: once the page boots, the page's session carries a CSRF
  // token, and API writes through it would need to send that token.
  let api = await request.newContext({ baseURL })
  await signInAs(api, people.actor)
  const others: APIRequestContext[] = [admin, api]
  let ids: SeedIds = {}
  let actor: Person = people.actor
  let space: Promise<Space> | null = null

  const scene: Scene = {
    page,
    context,
    get api() {
      return api
    },
    admin,
    baseURL,
    people,
    get actor() {
      return actor
    },
    get ids() {
      return ids
    },
    async seed(scenario) {
      ids = await reset(admin, baseURL, scenario)
      // `reset` deletes the demo users, which queues the same cleanup jobs as a demo load.
      settleJobs(baseURL)
      space = null
      await scene.signIn(testPeople.member)
      return ids
    },
    async signIn(person) {
      actor = person
      await context.clearCookies()
      await signInAs(context.request, person)
      api = await request.newContext({ baseURL })
      others.push(api)
      await signInAs(api, person)
    },
    space(community = ids.community ?? communities.commonRoom) {
      space ??= insert<{ name: string }>(admin, 'GP Project', { title: label, team: community }).then((doc) => ({
        name: String(doc.name),
        title: label,
      }))
      return space
    },
    find: (doctype, filters) => find(admin, doctype, filters),
    call: (ctx, method, args) => call(ctx, method, args),
    method: (ctx, doctype, name, method, args) => docMethod(ctx, doctype, name, method, args),
    insert: (ctx, doctype, doc) => insert(ctx, doctype, doc),
    async goto(path) {
      await page.goto(path.startsWith('/g') ? path : `/g${path}`)
    },
    async hold(url) {
      // The handler stays routed for the scene's life: unrouting lets a held request through.
      const held: Route[] = []
      let status: number | null = null
      let passing = false
      const fail = (route: Route) =>
        route.fulfill({
          status: status ?? 500,
          contentType: 'application/json',
          body: JSON.stringify({ exc_type: 'ServerError', message: 'Something went wrong' }),
        })
      await page.route(url, async (route) => {
        if (passing) await route.continue()
        else if (status === null) held.push(route)
        else await fail(route)
      })
      return {
        async release() {
          passing = true
          status = null
          await Promise.all(held.splice(0).map((route) => route.continue().catch(() => undefined)))
        },
        async abort(next = 500) {
          status = next
          passing = false
          await Promise.all(held.splice(0).map((route) => fail(route).catch(() => undefined)))
        },
      }
    },
    async settle(ms = SETTLE_MS) {
      await page.waitForTimeout(ms)
    },
    async as(person) {
      const other = await request.newContext({ baseURL })
      others.push(other)
      await signInAs(other, person)
      return other
    },
    async close() {
      await context.close()
      await Promise.all(others.map((other) => other.dispose()))
    },
  }
  return scene
}

/**
 * Replays the demo fixture, replacing every Gameplan row on the site. Takes
 * about ten seconds.
 *
 * Each replay queues about 560 background jobs: a search re-index per reply
 * and a link cleanup per deleted demo user. The queue refuses new jobs past
 * 550, and a running job holds SQLite's write lock for up to ten seconds, which
 * times out the page's own writes (a 508 at sign-in). The replay rebuilds the
 * search index itself, so the jobs are purged on both sides of it, and the
 * scene waits for the job the worker already started.
 */
function loadDemo(baseURL: string): void {
  // Background jobs from the last scene hold SQLite's write lock, so let them finish first.
  settleJobs(baseURL)
  // A past `seed()` gave the test personas cast names; left in place they show up twice in people pickers.
  const emails = JSON.stringify(Object.values(testPeople).map((person) => person.email))
  frappe(baseURL, 'execute', 'frappe.delete_doc', '--args', `["User", ${emails}]`, '--kwargs', '{"force": True, "ignore_missing": True}')
  frappe(baseURL, 'execute', 'gameplan.demo.demo.generate', '--kwargs', '{"force": True}')
  settleJobs(baseURL)
}

/** Drops queued background jobs, then waits for the one the worker already started. */
function settleJobs(baseURL: string): void {
  frappe(baseURL, 'purge-jobs')
  waitForIdleWorker()
}

/**
 * Runs a bench command for the site. A request the last scene's page left in
 * flight can still hold SQLite's write lock, so a "database is locked" failure
 * is retried a few times.
 */
function frappe(baseURL: string, ...args: string[]): void {
  if (!BENCH) throw new Error('UI_STATES_BENCH must name the Pilot bench that serves BASE_URL')
  const site = new URL(baseURL).hostname
  for (let attempt = 1; ; attempt++) {
    try {
      execFileSync(PILOT, ['-b', BENCH, 'frappe', '--site', site, ...args], { stdio: 'pipe', timeout: 120_000 })
      return
    } catch (error) {
      const { stdout, stderr, status, signal } = error as { stdout?: Buffer; stderr?: Buffer; status?: number; signal?: string }
      const output = `${stderr ?? ''}\n${stdout ?? ''}`
      if (attempt < 3 && output.includes('database is locked')) {
        Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 2_000)
        continue
      }
      // SQLite's SQL translator warns on every ALTER SEQUENCE; drop those lines so the real error shows.
      const noise = /ALTER SEQUENCE|unsupported syntax|^Syntax error in query:$/
      const tail = output.trim().split('\n').filter((line) => !noise.test(line.trim())).slice(-20).join('\n')
      throw new Error(`frappe ${args.slice(0, 2).join(' ')} failed (status ${status}, signal ${signal}):\n${tail}`)
    }
  }
}

/** Waits until no background job is running, by reading RQ's started-job registries. */
function waitForIdleWorker(): void {
  if (!BENCH) throw new Error('UI_STATES_BENCH must name the Pilot bench that serves BASE_URL')
  const config = readFileSync(resolve(dirname(dirname(PILOT)), 'benches', BENCH, 'bench.toml'), 'utf8')
  const port = config.match(/^queue_port\s*=\s*(\d+)/m)?.[1]
  if (!port) throw new Error(`No queue_port in ${BENCH}/bench.toml`)
  const redis = (...args: string[]) => execFileSync('redis-cli', ['-p', port, ...args], { encoding: 'utf8' }).trim()
  const deadline = Date.now() + 60_000
  while (Date.now() < deadline) {
    const registries = redis('--scan', '--pattern', 'rq:wip:*').split('\n').filter(Boolean)
    const running = registries.reduce((total, key) => total + Number(redis('zcard', key)), 0)
    if (running === 0) return
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 250)
  }
}

async function login(api: APIRequestContext): Promise<void> {
  await loginWithPassword(api, people.admin.email, ADMIN_PASSWORD)
}

/** SQLite answers 508 while a background job holds the write lock, so sign-in waits it out. */
async function loginWithPassword(api: APIRequestContext, usr: string, pwd: string): Promise<void> {
  for (let attempt = 1; ; attempt++) {
    const response = await api.post('/api/method/login', { data: { usr, pwd } })
    if (response.ok()) return
    if (response.status() !== 508 || attempt === 20) {
      throw new Error(`Signing in as ${usr} failed: ${response.status()}`)
    }
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
}

/** Demo people have no password; the dev user switcher starts a session for them. */
async function signInAs(api: APIRequestContext, person: Person): Promise<void> {
  if (person.password) return loginWithPassword(api, person.email, person.password)
  await login(api)
  await call(api, 'gameplan.dev_user_switcher.switch_user', { user: person.email })
}

/** Wipes Gameplan data, builds the scenario, then gives the personas and the community real names. */
async function reset(admin: APIRequestContext, baseURL: string, scenario?: Scenario): Promise<SeedIds> {
  const ids = await call<SeedIds>(admin, 'gameplan.ui_test_helpers.reset', scenario ? { scenario } : {})
  // The reset queues jobs that hold SQLite's write lock; the renames below would hit it.
  settleJobs(baseURL)
  for (const person of Object.values(testPeople)) {
    const [first_name, ...rest] = person.fullName.split(' ')
    await update(admin, 'User', person.email, { first_name, last_name: rest.join(' ') })
  }
  if (ids.community) await update(admin, 'GP Team', ids.community, { title: 'Moonhollow' })
  return ids
}

async function call<T>(api: APIRequestContext, method: string, args: Record<string, unknown> = {}): Promise<T> {
  const response = await api.post(`/api/method/${method}`, { data: args })
  if (!response.ok()) throw new Error(`${method} failed: ${response.status()} ${await response.text()}`)
  return ((await response.json()) as { message: T }).message
}

async function docMethod<T>(
  api: APIRequestContext,
  doctype: string,
  name: string,
  method: string,
  args: Record<string, unknown> = {},
): Promise<T> {
  const url = `/api/v2/document/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}/method/${method}`
  const response = await api.post(url, { data: args })
  if (!response.ok()) throw new Error(`${doctype}.${method} failed: ${response.status()} ${await response.text()}`)
  return ((await response.json()) as { data: T }).data
}

async function find(api: APIRequestContext, doctype: string, filters: Record<string, unknown>): Promise<string> {
  const params = new URLSearchParams({ filters: JSON.stringify(filters), fields: '["name"]', limit_page_length: '1' })
  const response = await api.get(`/api/resource/${encodeURIComponent(doctype)}?${params}`)
  if (!response.ok()) throw new Error(`Listing ${doctype} failed: ${response.status()} ${await response.text()}`)
  const [row] = ((await response.json()) as { data: { name: string | number }[] }).data
  if (!row) throw new Error(`No ${doctype} matches ${JSON.stringify(filters)}`)
  return String(row.name)
}

async function insert<T>(api: APIRequestContext, doctype: string, doc: Record<string, unknown>): Promise<T> {
  const response = await api.post(`/api/resource/${encodeURIComponent(doctype)}`, { data: doc })
  if (!response.ok()) throw new Error(`Inserting ${doctype} failed: ${response.status()} ${await response.text()}`)
  return ((await response.json()) as { data: T }).data
}

async function update(api: APIRequestContext, doctype: string, name: string, values: Record<string, unknown>): Promise<void> {
  const response = await api.put(`/api/resource/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}`, {
    data: values,
  })
  if (!response.ok()) throw new Error(`Updating ${doctype} ${name} failed: ${response.status()} ${await response.text()}`)
}
