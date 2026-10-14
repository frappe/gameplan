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

// What the server holds, so a failed save puts the sidebar back rather than lose it on reload.
let saved: string[] = []
// Saves can overlap and land out of order, so only a newer save replaces `saved`.
let lastSubmitted = 0
let lastSaved = 0

const persist = debounce((value: string[]) => {
  if (!profileName.value) return
  const submitted = ++lastSubmitted
  userProfiles.setValue
    .submit({ name: profileName.value, pinned_spaces: JSON.stringify(value) })
    .then(
      () => {
        if (submitted < lastSaved) return
        lastSaved = submitted
        saved = value
      },
      () => {
        if (pinned.value === value) pinned.value = saved
      },
    )
}, 500)

export function loadPinnedSpaces(value: unknown, currentProfileName = '') {
  profileName.value = currentProfileName
  if (!currentProfileName) return
  pinned.value = saved = normalizePinnedSpaces(parseStoredPins(value))
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
