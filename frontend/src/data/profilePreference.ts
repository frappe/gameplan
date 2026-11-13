import { computed } from 'vue'
import { useLocalStorage } from '@vueuse/core'
import { toast, useDoctype } from 'frappe-ui'
import { OptimisticSave } from '@/utils/optimisticSave'
import { sessionUserFromCookie } from '@/utils/sessionCookie'
import type { GPUserProfile } from '@/types/doctypes'

interface ProfilePreferenceOptions<T> {
  field: keyof GPUserProfile
  /** Names this browser's copy: `gameplan:<cacheKey>:<user>`. */
  cacheKey: string
  defaultValue: T
  normalize: (value: unknown) => T
  /** Turns the value into what the field stores. Booleans become 0 or 1 by default. */
  encode?: (value: T) => unknown
  /** The localStorage key this preference used when it was kept per device. */
  legacyKey?: string
  errorMessage?: string
}

const userProfiles = useDoctype<GPUserProfile>('GP User Profile')

/**
 * A preference saved on the user's GP User Profile, so every device shows the same value.
 *
 * This browser keeps a copy per user, so the first paint does not wait for the server.
 * Once the profile loads, the server value wins, unless a save is in flight.
 */
export class ProfilePreference<T> {
  private cached
  private profileName = ''
  private save: OptimisticSave<T>

  /** The value to show: a change the server has not answered yet, or the saved value. */
  readonly current

  constructor(private options: ProfilePreferenceOptions<T>) {
    this.cached = useLocalStorage<T>(
      `gameplan:${options.cacheKey}:${sessionUserFromCookie() ?? 'Guest'}`,
      options.defaultValue,
    )
    this.save = new OptimisticSave<T>({
      send: (value) => this.send(value),
      onError: () => toast.error(options.errorMessage ?? 'Could not save your preference'),
    })
    this.save.onSaved((value) => (this.cached.value = value))
    this.current = computed(() => options.normalize(this.save.shown(this.cached.value)))
  }

  /**
   * Applies the value from the session user's profile, which `get_user_info` returns.
   *
   * A value loaded during a save can have been read before the save landed, so it is
   * ignored; a successful save sets the value itself. Once idle, the server value wins,
   * so a change made on another device is kept. A value read before a save landed but
   * loaded just after is still applied: it shows the old value until the next load.
   */
  load(serverValue: unknown, profileName: string) {
    this.profileName = profileName
    if (!profileName || this.save.busy) return
    this.cached.value = this.options.normalize(serverValue)
    this.migrateLegacyValue()
  }

  set(value: T) {
    this.save.change(value)
  }

  private async send(value: T) {
    // Without a profile there is nowhere to save, so the value stays in this browser.
    if (!this.profileName) return
    const { field, encode = encodeScalar, legacyKey } = this.options
    await userProfiles.setValue.submit({ name: this.profileName, [field]: encode(value) })
    // The profile now holds a choice, so the old per-device value is not needed.
    if (legacyKey) removeStored(legacyKey)
  }

  // A value someone chose on this device before the preference moved to the profile is
  // kept, unless the profile already has a choice of its own. The old key is removed
  // only once the profile holds a value, so a failed save is retried on the next load.
  private migrateLegacyValue() {
    const { legacyKey, normalize, defaultValue } = this.options
    if (!legacyKey) return
    const legacy = readStored(legacyKey)
    if (legacy === null) return
    const value = normalize(legacy)
    if (this.cached.value === defaultValue && value !== defaultValue) this.set(value)
    else removeStored(legacyKey)
  }
}

export function normalizeBoolean(value: unknown) {
  return value === true || value === 1 || value === '1' || value === 'true'
}

function encodeScalar(value: unknown) {
  return typeof value === 'boolean' ? Number(value) : value
}

function readStored(key: string) {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function removeStored(key: string) {
  try {
    localStorage.removeItem(key)
  } catch {
    // Storage is blocked, so there is nothing to remove.
  }
}
