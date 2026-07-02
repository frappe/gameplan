import { createApp, type Component, type Plugin } from 'vue'
import './index.css'

if (import.meta.env.DEV) {
  await loadDevBootContext()
}

setupApp().catch((error) => {
  console.error('Failed to mount Gameplan', error)
})

async function loadDevBootContext() {
  const response = await fetch('/api/v2/method/gameplan.www.g.get_context_for_dev', {
    method: 'POST',
  })
  if (!response.ok) {
    throw new Error('Failed to load Gameplan dev boot context')
  }

  const responseBody = (await response.json()) as BootContextResponse
  const values = responseBody.message || responseBody.data || responseBody
  const windowValues = window as unknown as Record<string, unknown>
  for (let key in values) {
    windowValues[key] = values[key]
  }
}

type BootContext = Record<string, unknown>

interface BootContextResponse extends BootContext {
  data?: BootContext
  message?: BootContext
}

// Runs once boot values are on `window` (inline script in prod, the dev
// context call above in dev) so frappe-ui gets its full config in one place.
async function setupApp() {
  const [
    { default: App },
    { default: router },
    {
      Button,
      Input,
      TextInput,
      FormControl,
      ErrorMessage,
      Dialog,
      Alert,
      Badge,
      frappeRequest,
      pageMetaPlugin,
      FrappeUI,
    },
    { session },
    { initSocket },
    { default: resetDataMixin },
  ] = await Promise.all([
    import('./App.vue'),
    import('./router'),
    import('frappe-ui'),
    import('./data/session'),
    import('./socket'),
    import('./utils/resetDataMixin'),
  ])

  let globalComponents: Record<string, Component> = {
    Button,
    TextInput,
    Input,
    FormControl,
    ErrorMessage,
    Dialog,
    Alert,
    Badge,
  }
  let app = createApp(App)
  app.use(pageMetaPlugin as unknown as Plugin)
  app.mixin(resetDataMixin)
  for (let key in globalComponents) {
    app.component(key, globalComponents[key])
  }

  app.use(router)
  app.use(FrappeUI, {
    call: false,
    socketio: false,
    config: {
      resourceFetcher: frappeRequest,
      defaultListUrl: 'gameplan.extends.client.get_list',
      systemTimezone: window.system_timezone || null,
      maxFileSize: window.max_file_size ? Number(window.max_file_size) : null,
    },
  })
  if (!session.canBrowsePublicWeb) {
    initSocket()
  }
  app.mount('#app')

  // Sentry error logging. Loaded lazily (dynamic import) so the ~250 KB SDK stays
  // out of the entry chunk — it's the #1 resource on the initial critical path and
  // is only ever needed in production when a DSN is configured. The import fires
  // during setup so browser-tracing still attaches early enough to capture vitals.
  const sentryDsn = window.gameplan_frontend_sentry_dsn
  if (import.meta.env.PROD && sentryDsn) {
    import('@sentry/vue').then((Sentry) => {
      Sentry.init({
        app,
        dsn: sentryDsn,
        integrations: [Sentry.browserTracingIntegration({ router })],
        tracesSampleRate: 1.0,
      })
    })
  }
}
