/**
 * Reading a Frappe error the way a person should see it.
 *
 * `frappeRequest` puts the clean `frappe.throw()` text on the error's `messages`
 * array (parsed out of `_server_messages`). The plain `message` is the noisy
 * "<method> <ExcType>" string, so prefer `messages` and fall back to it.
 */

interface FrappeError extends Error {
  exc_type?: string
  messages?: unknown
}

/** The server's own wording for a failure, or '' when it did not send one. */
export function getServerErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    let messages = asFrappeError(error).messages
    if (Array.isArray(messages)) {
      let text = messages.filter((message): message is string => typeof message === 'string')
      if (text.length) return stripHtml(text.join('\n'))
    }
    if (error.message) return stripHtml(error.message)
  }
  return typeof error === 'string' ? error : ''
}

/** True when the request failed because the user is not allowed to do it. */
export function isPermissionError(error: unknown): boolean {
  return error instanceof Error && asFrappeError(error).exc_type === 'PermissionError'
}

function asFrappeError(error: Error): FrappeError {
  return error as FrappeError
}

function stripHtml(value: string) {
  return value.replace(/<[^>]*>/g, '').trim()
}
