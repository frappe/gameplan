/**
 * Classifying a Frappe error, rather than reading its text.
 *
 * For the wording to put in front of a person, use `extractServerMessage` from `@/utils`.
 */

interface FrappeError extends Error {
  exc_type?: string
}

/** True when the request failed because the user is not allowed to do it. */
export function isPermissionError(error: unknown): boolean {
  return error instanceof Error && (error as FrappeError).exc_type === 'PermissionError'
}
