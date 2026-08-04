import { ref } from 'vue'
import type { ProfileFieldEditor, ProfileFieldUpdate } from '../types'

/**
 * Writes a bound field to the profile, tracking whether a write is in flight.
 *
 * Every bound editor saves the same way and needs the same busy flag, which is
 * the whole of what they share. The failure is already reported by the field
 * editor and the card keeps showing the stored value, so `commit` swallows the
 * rejection on purpose: the control holds on to the draft the user typed rather
 * than snapping back to a value they did not ask for.
 */
export function useBoundFieldSave(fieldEditor: () => ProfileFieldEditor) {
  const saving = ref(false)

  async function save(update: ProfileFieldUpdate) {
    saving.value = true
    try {
      await fieldEditor().save(update)
    } finally {
      saving.value = false
    }
  }

  function commit(update: ProfileFieldUpdate) {
    save(update).catch(() => {})
  }

  return { saving, commit, save }
}
