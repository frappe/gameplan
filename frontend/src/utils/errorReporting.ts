/// <reference types="vite/client" />
/**
 * One funnel for errors, including the ones the UI swallows.
 *
 * Most failures here are caught and turned into a message next to a button, so nothing
 * about them survives the tab: no exception, no trace, nothing on the server. That is
 * why an intermittent report ("it did not post the first time") is impossible to chase.
 * `captureError` is the reporting call for those handled paths; the global handlers
 * installed below cover everything that reaches the browser uncaught.
 *
 * Every report goes to the site's Error Log through `gameplan.api.log_client_error`, and
 * to Sentry as well when a DSN is configured. The server sink is the one that always
 * works, since most sites run without a DSN.
 */
import { call } from 'frappe-ui'
import type { App } from 'vue'
import type { Router } from 'vue-router'

const LOG_CLIENT_ERROR = 'gameplan.api.log_client_error'

/** Per page load. A render loop can raise the same error thousands of times; the server
 *  has its own hourly quota, and this keeps us from spending the request budget on it. */
const MAX_REPORTS_PER_PAGE_LOAD = 20

export interface ErrorContext {
  /** What the user was doing, e.g. `publish-discussion`. Becomes the Error Log title. */
  action: string
  [key: string]: unknown
}

type SentryModule = typeof import('@sentry/vue')

let sentry: SentryModule | null = null
let reportCount = 0
const reportedFingerprints = new Set<string>()

/**
 * Report an error the UI handled itself. Logs to the console, sends it to the server, and
 * forwards it to Sentry when it is loaded. Never throws and never rejects: reporting a
 * failure must not turn into a second failure.
 */
export function captureError(error: unknown, context: ErrorContext): void {
  try {
    console.error(`[${context.action}]`, error)
    sentry?.captureException(error, { extra: { ...context } })
    sendToServer(error, context)
  } catch (reportingError) {
    console.error('Error reporting failed', reportingError)
  }
}

/**
 * Install the global handlers and start Sentry. Called before mount, so an error thrown
 * during setup is still reported — the Sentry SDK is a lazy import (~250 KB off the entry
 * chunk) and only attaches once it lands.
 */
export function installErrorReporting(app: App, router: Router): void {
  const previousHandler = app.config.errorHandler
  app.config.errorHandler = (error, instance, info) => {
    captureError(error, { action: 'vue-error-handler', info })
    previousHandler?.(error, instance, info)
  }

  window.addEventListener('error', (event) => {
    // A failed <img>/<script> load fires a plain Event on the same channel. It carries no
    // error and no message, so there is nothing to report.
    if (!(event instanceof ErrorEvent)) return
    captureError(event.error ?? event.message, {
      action: 'uncaught-error',
      source: event.filename ? `${event.filename}:${event.lineno}:${event.colno}` : undefined,
    })
  })

  window.addEventListener('unhandledrejection', (event) => {
    captureError(event.reason, { action: 'unhandled-rejection' })
  })

  if (import.meta.env.PROD && window.gameplan_frontend_sentry_dsn) {
    import('@sentry/vue').then((Sentry) => {
      Sentry.init({
        app,
        dsn: window.gameplan_frontend_sentry_dsn,
        integrations: [Sentry.browserTracingIntegration({ router })],
        tracesSampleRate: 1.0,
      })
      sentry = Sentry
    })
  }
}

function sendToServer(error: unknown, context: ErrorContext): void {
  const message = describe(error)
  const fingerprint = `${context.action}::${message.split('\n')[0]}`
  // One report per distinct error per page load: a retried action repeats the same
  // failure, and twenty copies of it say nothing the first one did not.
  if (reportedFingerprints.has(fingerprint)) return
  if (reportCount >= MAX_REPORTS_PER_PAGE_LOAD) return
  reportedFingerprints.add(fingerprint)
  reportCount += 1

  call(LOG_CLIENT_ERROR, {
    message,
    context: { ...context, url: window.location.href, user_agent: navigator.userAgent },
  }).catch(() => {
    // The sink is unreachable (offline, or the request that failed is failing again).
    // Dropping the report is the only safe move: retrying it would loop.
  })
}

/** A single string carrying the name, the message and the stack, for anything thrown. */
function describe(error: unknown): string {
  if (error instanceof Error) {
    const header = `${error.name}: ${error.message}`
    return error.stack?.includes(error.message) ? error.stack : `${header}\n${error.stack ?? ''}`
  }
  if (typeof error === 'string') return error
  try {
    return JSON.stringify(error)
  } catch {
    return String(error)
  }
}
