/** Icon + label helpers for the Public/Private visibility of communities and spaces. */

export function visibilityLabel(isPrivate?: boolean | 0 | 1) {
  return isPrivate ? 'Private' : 'Public'
}

/** Icon for a visibility filter tab whose value is 'All' | 'Public' | 'Private' (no icon for 'All'). */
export function visibilityFilterIcon(value: unknown) {
  if (value === 'Private') return 'lucide-lock'
  if (value === 'Public') return 'lucide-globe-2'
  return undefined
}
