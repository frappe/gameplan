/**
 * Visibility tiers of communities and spaces, and how the UI shows them. Mirrors
 * gameplan/public_access.py.
 *
 * - Anonymous: anyone with the link, no account needed.
 * - General: any signed-in Gameplan user.
 * - Member Access: only people on the member list.
 */

export const VISIBILITY_ANONYMOUS = 'Anonymous'
export const VISIBILITY_GENERAL = 'General'
export const VISIBILITY_MEMBER_ACCESS = 'Member Access'

export type Visibility =
  | typeof VISIBILITY_ANONYMOUS
  | typeof VISIBILITY_GENERAL
  | typeof VISIBILITY_MEMBER_ACCESS

const VISIBILITY_TIERS: readonly string[] = [
  VISIBILITY_ANONYMOUS,
  VISIBILITY_GENERAL,
  VISIBILITY_MEMBER_ACCESS,
]

/** `value` as a tier. Anything empty or unknown reads as Member Access, the strictest. */
export function visibilityTier(value?: string | null): Visibility {
  return value && VISIBILITY_TIERS.includes(value)
    ? (value as Visibility)
    : VISIBILITY_MEMBER_ACCESS
}

/** Whether only the people on the member list may read something with this tier. */
export function isMemberAccess(value?: string | null): boolean {
  return visibilityTier(value) === VISIBILITY_MEMBER_ACCESS
}

export function visibilityLabel(value?: string | null): Visibility {
  return visibilityTier(value)
}

export function visibilityIcon(value?: string | null) {
  const tier = visibilityTier(value)
  if (tier === VISIBILITY_ANONYMOUS) return 'lucide-earth'
  if (tier === VISIBILITY_GENERAL) return 'lucide-users'
  return 'lucide-lock'
}

/** Icon for a visibility filter tab: a tier, or 'All' (no icon). */
export function visibilityFilterIcon(value: unknown) {
  return typeof value === 'string' && VISIBILITY_TIERS.includes(value)
    ? visibilityIcon(value)
    : undefined
}
