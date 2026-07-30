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
  'gameplan:notification_count_changed': void
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

export function initSocket() {
  let host = window.location.hostname
  let siteName = window.site_name
  let port = window.location.port ? `:${socketio_port}` : ''
  let protocol = port ? 'http' : 'https'
  let url = `${protocol}://${host}${port}/${siteName}`

  socket = io(url, {
    withCredentials: true,
    reconnectionAttempts: 5,
  })
  // Attach one dispatcher per known event. socket.io keeps these across reconnects, so unlike
  // document rooms (see subscribeToDoc) they never need re-attaching.
  for (const event of GAMEPLAN_SOCKET_EVENTS) {
    socket.on(event, (payload: never) => {
      listeners.get(event)?.forEach((handler) => {
        try {
          handler(payload)
        } catch (error) {
          // One bad listener must not skip the rest, nor bubble into socket.io's handler.
          console.error(`Listener for "${event}" failed`, error)
        }
      })
    })
  }
  return socket
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
