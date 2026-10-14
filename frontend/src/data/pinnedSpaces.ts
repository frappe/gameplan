import { computed, ref } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import { debounce, toast, useDoctype } from 'frappe-ui'
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
// One save at a time, so saves cannot land out of order. Edits made meanwhile go out after it.
let saving = false

const persist = debounce(save, 500)

function save() {
  if (!profileName.value || saving || sameIds(pinned.value, saved)) return
  const value = [...pinned.value]
  saving = true
  userProfiles.setValue
    .submit({ name: profileName.value, pinned_spaces: JSON.stringify(value) })
    .then(
      () => {
        saved = value
      },
      () => {
        // Keep a newer edit; it is sent next.
        if (sameIds(pinned.value, value)) pinned.value = saved
        toast.error('Could not save your pinned spaces')
      },
    )
    .finally(() => {
      saving = false
      save()
    })
}

export function loadPinnedSpaces(value: unknown, currentProfileName = '') {
  profileName.value = currentProfileName
  if (!currentProfileName) return
  pinned.value = saved = normalizePinnedSpaces(parseStoredPins(value))
}

export function toggleSpacePinned(spaceId: string) {
  pinned.value = isSpacePinned(spaceId)
    ? pinned.value.filter((id) => id !== spaceId)
    : [...pinned.value, spaceId]
  persist()
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

function sameIds(a: string[], b: string[]) {
  return a.length === b.length && a.every((id, i) => id === b[i])
}

function sessionUserFromCookie() {
  let cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
  return cookies.get('user_id') || 'Guest'
}
