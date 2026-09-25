import { computed, ref } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import { debounce, useDoctype } from 'frappe-ui'
import type { GPUserProfile } from '@/types/doctypes'

const pinned = useLocalStorage<string[]>(`gameplan:pinnedSpaces:${sessionUserFromCookie()}`, [])
const profileName = ref('')
const userProfiles = useDoctype<GPUserProfile>('GP User Profile')

const pinnedLookup = computed(() => new Set(pinned.value))

export const pinnedSpaceIds = computed(() => pinned.value)

export function isSpacePinned(spaceId: string) {
  return pinnedLookup.value.has(spaceId)
}

const persist = debounce((value: string[]) => {
  if (!profileName.value) return
  userProfiles.setValue
    .submit({ name: profileName.value, pinned_spaces: JSON.stringify(value) })
    .catch(() => {})
}, 500)

export function loadPinnedSpaces(value: unknown, currentProfileName = '') {
  profileName.value = currentProfileName
  if (!currentProfileName) return
  pinned.value = normalizePinnedSpaces(parseStoredPins(value))
}

export function toggleSpacePinned(spaceId: string) {
  pinned.value = isSpacePinned(spaceId)
    ? pinned.value.filter((id) => id !== spaceId)
    : [...pinned.value, spaceId]
  persist(pinned.value)
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
