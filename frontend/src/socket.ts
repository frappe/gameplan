import type { Socket } from 'socket.io-client'
import { socketio_port } from '../../../../sites/common_site_config.json'

/** Payload published by GP Activity on every new discussion/comment activity.
 * Mirrors gameplan/mixins/activity.py — keep field names in sync; a rename there
 * would otherwise silently break live comment updates with no type error. */
export type NewActivityEvent = {
  reference_doctype: string
  reference_name: string
}

/** Frappe's events for one document, received after `subscribeToDoc` joins its room. */
export type DocRoomEvents = {
  new_activity: NewActivityEvent
  doc_update: { doctype?: string; name?: string | number }
}

/**
 * Every realtime event Gameplan's own backend publishes, and what each one carries.
 *
 * Mirrors gameplan/realtime.py — renaming an event means changing both sides. Each event
 * names what changed, not what to refetch: the listener decides that, because only the
 * client knows how it stores the data.
 *
 * Frappe's own events (`new_activity`, `doc_update`, ...) are not listed here. Components
 * listen for those with `onDocEvent()`, since they are scoped to a document room the
 * component subscribes to for its own lifetime.
 */
export type GameplanSocketEvents = {
  'gameplan:unread_counts_changed': void
  /** `count` is the recipient's unread notification count after the change. */
  'gameplan:notification_count_changed': { count: number }
  'gameplan:users_changed': void
}

type SocketEventName = keyof GameplanSocketEvents

let socket: Socket | null = null

// Every socket event handler, by event name. See `onSocket` for why they live here.
const listeners = new Map<string, Set<(payload: never) => void>>()
const reconnectListeners = new Set<() => void>()

const HANDSHAKE_RETRY_DELAY = 5000

/** Listen for a Gameplan backend event. Returns an unsubscribe function. */
export function onSocketEvent<K extends SocketEventName>(
  event: K,
  handler: (payload: GameplanSocketEvents[K]) => void,
) {
  return onSocket(event, handler)
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

/**
 * Run `handler` for every `event` the socket receives. Returns an unsubscribe function.
 *
 * Handlers live in this module's own registry rather than on the socket, which buys three
 * things. Registration order does not matter: `initSocket()` runs after the first page draws,
 * long after module-level code in `data/*.ts` has run, so a bare `socket.on()` there would attach
 * to nothing. Unsubscribing removes exactly one handler — `socket.off(event)` drops every
 * listener for that event, so two components listening to the same one clobber each other.
 * And one dispatcher per event runs its handlers through `runEach`, so a handler that throws
 * cannot stop the others.
 */
function onSocket(event: string, handler: (payload: never) => void) {
  let handlers = listeners.get(event)
  if (!handlers) {
    handlers = new Set()
    listeners.set(event, handlers)
    if (socket) attachDispatcher(socket, event, handlers)
  }
  handlers.add(handler)
  return () => {
    handlers.delete(handler)
  }
}

// socket.io keeps listeners across reconnects, so a dispatcher is attached once per event.
function attachDispatcher(
  appSocket: Socket,
  event: string,
  handlers: Set<(payload: never) => void>,
) {
  appSocket.on(event, (payload: never) => {
    runEach(handlers, `Listener for "${event}"`, payload)
  })
}

/**
 * Listen for a Frappe event in a document room joined with `subscribeToDoc`. Returns an
 * unsubscribe function. Safe to call before the socket exists.
 */
export function onDocEvent<K extends keyof DocRoomEvents>(
  event: K,
  handler: (payload: DocRoomEvents[K]) => void,
) {
  return onSocket(event, handler)
}

/** Connect to the realtime server. socket.io's code downloads here, not with the app. */
export async function initSocket() {
  const { io } = await import('socket.io-client')

  let host = window.location.hostname
  let siteName = window.site_name
  let port = window.location.port ? `:${socketio_port}` : ''
  let protocol = port ? 'http' : 'https'
  let url = `${protocol}://${host}${port}/${siteName}`

  // No cap on reconnection attempts: a laptop sleep or a server deploy outlasts a small cap,
  // and a socket that stops retrying leaves every live count frozen until a page reload.
  const appSocket = io(url, { withCredentials: true })
  socket = appSocket
  for (const [event, handlers] of listeners) attachDispatcher(appSocket, event, handlers)
  // Cypress feeds fake server events through the real socket (see poll-lifecycle.cy.ts).
  if (window.Cypress) window.gameplanSocket = appSocket

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
  const stopResubscribing = onSocket('connect', subscribe)

  return () => {
    stopResubscribing()
    socket?.emit('doc_unsubscribe', doctype, name)
  }
}
