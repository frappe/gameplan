import { computed, ref } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import { toast, useDoctype } from 'frappe-ui'
import { OptimisticSave } from '@/utils/optimisticSave'
import type { GPUserProfile } from '@/types/doctypes'

const pinned = useLocalStorage<string[]>(`gameplan:pinnedSpaces:${sessionUserFromCookie()}`, [])
const profileName = ref('')
const userProfiles = useDoctype<GPUserProfile>('GP User Profile')

const pinnedLookup = computed(() => new Set(pinned.value))

export const pinnedSpaceIds = computed(() => pinned.value)

export function isSpacePinned(spaceId: string) {
  return pinnedLookup.value.has(spaceId)
}

const pinSave = new OptimisticSave<string[]>({
  read: () => pinned.value,
  write: (value) => (pinned.value = value),
  // Without a profile there is nowhere to save, so the pins stay in this browser.
  send: (value) =>
    profileName.value
      ? userProfiles.setValue.submit({
          name: profileName.value,
          pinned_spaces: JSON.stringify(value),
        })
      : Promise.resolve(),
  onError: () => toast.error('Could not save your pinned spaces'),
})
// Set by the first toggle. From then on this session's pins are the newest: a server
// copy loaded later can have been read before one of its saves landed.
let pinnedHere = false

export function loadPinnedSpaces(value: unknown, currentProfileName = '') {
  profileName.value = currentProfileName
  if (!currentProfileName || pinnedHere) return
  pinned.value = normalizePinnedSpaces(parseStoredPins(value))
}

export function toggleSpacePinned(spaceId: string) {
  pinnedHere = true
  pinSave.change(
    isSpacePinned(spaceId)
      ? pinned.value.filter((id) => id !== spaceId)
      : [...pinned.value, spaceId],
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

function sessionUserFromCookie() {
  let cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
  return cookies.get('user_id') || 'Guest'
}
