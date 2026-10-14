/**
 * Classifying a Frappe error, rather than reading its text.
 *
 * For the wording to put in front of a person, use `extractServerMessage` from `@/utils`.
 */

interface FrappeError extends Error {
  exc_type?: string
}

/** The server exception a failed request carries, from either frappe-ui request path:
 *  `exc_type` from `call`, `type` from the v2 document and method APIs. */
export function errorType(error: unknown): string | undefined {
  const e = error as { type?: string; exc_type?: string } | null
  return e?.exc_type ?? e?.type
}

/** True when the request failed because the user is not allowed to do it. */
export function isPermissionError(error: unknown): boolean {
  return error instanceof Error && (error as FrappeError).exc_type === 'PermissionError'
}
