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

export type VisibilityFilter = 'All' | Visibility | 'Archived'
type VisibleRecord = { visibility?: string | null; archived_at?: string | null }

export const VISIBILITY_TIERS: readonly Visibility[] = [
  VISIBILITY_ANONYMOUS,
  VISIBILITY_GENERAL,
  VISIBILITY_MEMBER_ACCESS,
]

/** `value` as a tier. Anything empty or unknown reads as Member Access, the strictest. */
export function visibilityTier(value?: string | null): Visibility {
  return value && VISIBILITY_TIERS.includes(value as Visibility)
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

/** What each tier means, as the UI explains it. */
export const VISIBILITY_DESCRIPTIONS: Record<Visibility, string> = {
  [VISIBILITY_ANONYMOUS]: 'Anyone with the link, no account needed',
  [VISIBILITY_GENERAL]: 'Any signed-in Gameplan user',
  [VISIBILITY_MEMBER_ACCESS]: 'Only people on the explicit member list',
}

/**
 * The tiers a creation form offers. Only a Gameplan Admin may create something on the
 * Anonymous tier; the server refuses it from anyone else.
 */
export function creatableVisibilityOptions(isAdmin: boolean) {
  const tiers: Visibility[] = isAdmin
    ? [VISIBILITY_GENERAL, VISIBILITY_MEMBER_ACCESS, VISIBILITY_ANONYMOUS]
    : [VISIBILITY_GENERAL, VISIBILITY_MEMBER_ACCESS]
  return tiers.map((tier) => ({
    label: `${tier} — ${VISIBILITY_DESCRIPTIONS[tier]}`,
    value: tier,
  }))
}

export function matchesVisibility(record: VisibleRecord, filter: VisibilityFilter) {
  if (filter === 'Archived') return Boolean(record.archived_at)
  return !record.archived_at && (filter === 'All' || visibilityTier(record.visibility) === filter)
}

export function visibilityFilterOptions(records: VisibleRecord[]) {
  const active = records.filter((record) => !record.archived_at)
  const archived = records.length - active.length
  return [
    { label: `All (${active.length})`, value: 'All' },
    ...VISIBILITY_TIERS.map((tier) => ({
      label: `${tier} (${active.filter((record) => visibilityTier(record.visibility) === tier).length})`,
      value: tier,
    })),
    ...(archived ? [{ label: `Archived (${archived})`, value: 'Archived' }] : []),
  ]
}
