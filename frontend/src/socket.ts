import { io, type Socket } from 'socket.io-client'
import { socketio_port } from '../../../../sites/common_site_config.json'

/** Payload published by GP Activity on every new discussion/comment activity.
 * Mirrors gameplan/mixins/activity.py — keep field names in sync; a rename there
 * would otherwise silently break live comment updates with no type error. */
export type NewActivityEvent = {
  reference_doctype: string
  reference_name: string
}

/**
 * Every realtime event Gameplan's own backend publishes, and what each one carries.
 *
 * Mirrors gameplan/realtime.py — renaming an event means changing both sides. Each event
 * names what changed, not what to refetch: the listener decides that, because only the
 * client knows how it stores the data.
 *
 * Frappe's own events (`new_activity`, `doc_update`, ...) are not listed here. Components
 * that want those still reach for `useSocket()` directly, since they are scoped to a
 * document room the component subscribes to for its own lifetime.
 */
export type GameplanSocketEvents = {
  'gameplan:unread_counts_changed': void
  /** `count` is the recipient's unread notification count after the change. */
  'gameplan:notification_count_changed': { count: number; force_refresh?: boolean }
  'gameplan:users_changed': void
}

type SocketEventName = keyof GameplanSocketEvents

// The runtime twin of GameplanSocketEvents: `satisfies` makes TypeScript reject a name that
// isn't in the type, and every key in the type must appear here or nothing dispatches it.
const GAMEPLAN_SOCKET_EVENTS = [
  'gameplan:unread_counts_changed',
  'gameplan:notification_count_changed',
  'gameplan:users_changed',
] as const satisfies readonly SocketEventName[]

let socket: Socket | null = null

const listeners = new Map<SocketEventName, Set<(payload: any) => void>>()
const reconnectListeners = new Set<() => void>()

const HANDSHAKE_RETRY_DELAY = 5000

/**
 * Listen for a backend event. Returns an unsubscribe function.
 *
 * Handlers live in this module's own registry rather than on the socket, which buys two
 * things. Registration order does not matter: `initSocket()` runs inside `setupApp()`, long
 * after module-level code in `data/*.ts` has run, so a bare `socket.on()` there would attach
 * to nothing. And unsubscribing removes exactly one handler — `socket.off(event)` drops every
 * listener for that event, so two components listening to the same one clobber each other.
 */
export function onSocketEvent<K extends SocketEventName>(
  event: K,
  handler: (payload: GameplanSocketEvents[K]) => void,
) {
  let handlers = listeners.get(event)
  if (!handlers) {
    handlers = new Set()
    listeners.set(event, handlers)
  }
  handlers.add(handler)
  return () => {
    handlers.delete(handler)
  }
}

/**
 * Run `handler` each time the socket reconnects after a drop. Returns an unsubscribe function.
 *
 * Events published while the socket was down are gone for good, so data kept live by a
 * push has to refetch here or it stays stale until the next push or a page reload.
 */
export function onSocketReconnect(handler: () => void) {
  reconnectListeners.add(handler)
  return () => {
    reconnectListeners.delete(handler)
  }
}

export function initSocket() {
  let host = window.location.hostname
  let siteName = window.site_name
  let port = window.location.port ? `:${socketio_port}` : ''
  let protocol = port ? 'http' : 'https'
  let url = `${protocol}://${host}${port}/${siteName}`

  // No cap on reconnection attempts: a laptop sleep or a server deploy outlasts a small cap,
  // and a socket that stops retrying leaves every live count frozen until a page reload.
  const appSocket = io(url, { withCredentials: true })
  socket = appSocket

  // `connect`, not the Manager's `reconnect`: the server joins this user's room during the
  // handshake, so refetching any earlier could miss a push sent before the room was joined.
  let hasConnected = false
  appSocket.on('connect', () => {
    if (hasConnected) runEach(reconnectListeners, 'Socket reconnect listener')
    hasConnected = true
  })

  // Frappe rejects the handshake when its auth call to the web server fails, which happens
  // while a deploy restarts the web server. socket.io never retries a rejected handshake.
  // Retrying is safe: a logged-out session passes auth as Guest instead of failing.
  appSocket.on('connect_error', () => {
    if (!appSocket.active) setTimeout(() => appSocket.connect(), HANDSHAKE_RETRY_DELAY)
  })

  // Attach one dispatcher per known event. socket.io keeps these across reconnects, so unlike
  // document rooms (see subscribeToDoc) they never need re-attaching.
  for (const event of GAMEPLAN_SOCKET_EVENTS) {
    appSocket.on(event, (payload: never) => {
      runEach(listeners.get(event) ?? [], `Listener for "${event}"`, payload)
    })
  }
  return appSocket
}

/**
 * Call every handler with `args`. One that throws is logged, so it cannot skip the rest or
 * bubble into the caller, which for socket events is socket.io's own handler.
 */
export function runEach<A extends unknown[]>(
  handlers: Iterable<(...args: A) => void>,
  label: string,
  ...args: A
) {
  for (const handler of [...handlers]) {
    try {
      handler(...args)
    } catch (error) {
      console.error(`${label} failed`, error)
    }
  }
}

export function useSocket() {
  return socket
}

/**
 * Join a document's realtime room so this tab receives events published for it
 * (see `frappe.publish_realtime(..., doctype=, docname=)`).
 *
 * The realtime server permission-checks every subscription, so a user who cannot read
 * the document simply never joins. Re-subscribes on reconnect, since rooms are lost
 * when the socket drops. Returns the unsubscribe function.
 */
export function subscribeToDoc(doctype: string, name: string) {
  const subscribe = () => socket?.emit('doc_subscribe', doctype, name)
  subscribe()
  socket?.on('connect', subscribe)

  return () => {
    socket?.off('connect', subscribe)
    socket?.emit('doc_unsubscribe', doctype, name)
  }
}
