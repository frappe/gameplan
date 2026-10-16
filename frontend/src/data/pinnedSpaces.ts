import { computed, ref } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import { toast, useDoctype } from 'frappe-ui'
import { OptimisticSave } from '@/utils/optimisticSave'
import type { GPUserProfile } from '@/types/doctypes'

// The saved pins. A pin the server has not accepted yet is only in `shownPins`.
const pinned = useLocalStorage<string[]>(`gameplan:pinnedSpaces:${sessionUserFromCookie()}`, [])
const profileName = ref('')
const userProfiles = useDoctype<GPUserProfile>('GP User Profile')

const pinSave = new OptimisticSave<string[]>({
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
pinSave.onSaved((value) => (pinned.value = value))

const shownPins = computed(() => pinSave.shown(pinned.value))
const pinnedLookup = computed(() => new Set(shownPins.value))

export const pinnedSpaceIds = shownPins

export function isSpacePinned(spaceId: string) {
  return pinnedLookup.value.has(spaceId)
}

// A server copy loaded during a save can have been read before the save landed, so
// it is ignored; a successful save sets the pins itself. Once idle, the server copy
// wins, so a change made in another browser is kept. A copy read before a save landed
// but loaded just after is still applied: it shows the old pins until the next load.
export function loadPinnedSpaces(value: unknown, currentProfileName = '') {
  profileName.value = currentProfileName
  if (!currentProfileName || pinSave.busy) return
  pinned.value = normalizePinnedSpaces(parseStoredPins(value))
}

export function toggleSpacePinned(spaceId: string) {
  pinSave.change(
    isSpacePinned(spaceId)
      ? shownPins.value.filter((id) => id !== spaceId)
      : [...shownPins.value, spaceId],
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
