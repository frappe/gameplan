import { computed } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import { toast, useDoctype } from 'frappe-ui'
import { OptimisticSave } from '@/utils/optimisticSave'
import type { GPUserProfile } from '@/types/doctypes'

type PreferenceField = 'show_all_discussions' | 'space_sidebar_sort' | 'hide_inactive_spaces'

interface ProfilePreferenceOptions<T extends string | boolean> {
  field: PreferenceField
  defaultValue: T
  normalize: (value: unknown) => T
  /** The localStorage key this preference used when it was kept per device. */
  legacyKey: string
}

const userProfiles = useDoctype<GPUserProfile>('GP User Profile')

/**
 * A preference saved on the user's GP User Profile, so every device shows the same value.
 *
 * This browser keeps a copy per user, so the first paint does not wait for the server.
 * Once the profile loads, the server value wins, unless a save is in flight.
 */
export class ProfilePreference<T extends string | boolean> {
  private cached
  private profileName = ''
  private save: OptimisticSave<T>

  /** The value to show: a change the server has not answered yet, or the saved value. */
  readonly current

  constructor(private options: ProfilePreferenceOptions<T>) {
    this.cached = useLocalStorage<T>(
      `gameplan:${options.field}:${sessionUserFromCookie()}`,
      options.defaultValue,
    )
    this.save = new OptimisticSave<T>({
      send: (value) => this.send(value),
      onError: () => toast.error('Could not save your preference'),
    })
    this.save.onSaved((value) => (this.cached.value = value))
    this.current = computed(() => options.normalize(this.save.shown(this.cached.value)))
  }

  /** Applies the value from the session user's profile, which `get_user_info` returns. */
  load(serverValue: unknown, profileName: string) {
    this.profileName = profileName
    if (!profileName || this.save.busy) return
    this.cached.value = this.options.normalize(serverValue)
    this.migrateLegacyValue()
  }

  set(value: T) {
    this.save.change(value)
  }

  private send(value: T) {
    // Without a profile there is nowhere to save, so the value stays in this browser.
    if (!this.profileName) return Promise.resolve()
    return userProfiles.setValue.submit({
      name: this.profileName,
      [this.options.field]: typeof value === 'boolean' ? Number(value) : value,
    })
  }

  // Runs once per browser: the old key is removed. A value someone chose on this device
  // before the preference moved to the profile is kept, unless the profile already has
  // a choice of its own.
  private migrateLegacyValue() {
    const { legacyKey, normalize, defaultValue } = this.options
    const legacy = readAndRemove(legacyKey)
    if (legacy === null) return
    const value = normalize(legacy)
    if (this.cached.value === defaultValue && value !== defaultValue) this.set(value)
  }
}

export function normalizeBoolean(value: unknown) {
  return value === true || value === 1 || value === '1' || value === 'true'
}

function readAndRemove(key: string) {
  try {
    const value = localStorage.getItem(key)
    localStorage.removeItem(key)
    return value
  } catch {
    return null
  }
}

function sessionUserFromCookie() {
  let cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
  return cookies.get('user_id') || 'Guest'
}
