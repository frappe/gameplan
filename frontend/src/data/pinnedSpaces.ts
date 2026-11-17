import { computed } from 'vue'
import { ProfilePreference } from './profilePreference'

const pins = new ProfilePreference<string[]>({
  field: 'pinned_spaces',
  cacheKey: 'pinnedSpaces',
  defaultValue: [],
  normalize: (value) => normalizePinnedSpaces(parseStoredPins(value)),
  encode: (value) => JSON.stringify(value),
  errorMessage: 'Could not save your pinned spaces',
})
const pinnedLookup = computed(() => new Set(pins.current.value))

export const pinnedSpaceIds = pins.current

export function isSpacePinned(spaceId: string) {
  return pinnedLookup.value.has(spaceId)
}

export function loadPinnedSpaces(value: unknown, currentProfileName = '') {
  pins.load(value, currentProfileName)
}

export function toggleSpacePinned(spaceId: string) {
  pins.set(
    isSpacePinned(spaceId)
      ? pins.current.value.filter((id) => id !== spaceId)
      : [...pins.current.value, spaceId],
  )
}

function parseStoredPins(value: unknown): unknown {
  if (typeof value !== 'string') return value
  try {
    return JSON.parse(value)
  } catch {
    return null
  }
}

function normalizePinnedSpaces(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  const seen = new Set<string>()
  return value.filter((id): id is string => {
    if (typeof id !== 'string' || !id || seen.has(id)) return false
    seen.add(id)
    return true
  })
}
