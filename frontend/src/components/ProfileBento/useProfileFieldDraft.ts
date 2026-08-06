import { computed, ref, type ComputedRef, type Ref } from 'vue'
import type {
  ProfileFieldDraft,
  ProfileFieldEditor,
  ProfileFieldStage,
  ProfileFieldUpdate,
  ProfileFieldValues,
} from './types'

type StagedField = ProfileFieldUpdate['field']
type StagedUpdates = Partial<Record<StagedField, ProfileFieldStage>>

export interface ProfileFieldDraftOptions {
  /** Writes one field to its document. Absent while the viewer may not edit. */
  editor: () => ProfileFieldEditor | undefined
  /** What the server currently holds for every bound field. */
  stored: () => ProfileFieldValues
  /** Re-reads the documents once the writes have landed. */
  onSaved: () => void | Promise<void>
}

/**
 * Bound-field edits held locally until the customize page's Save is pressed.
 *
 * Editing used to write straight through on blur, which made the panel's controls
 * behave unlike everything else on that screen and, worse, was unreliable: the
 * doc store publishes the same profile twice, from the IndexedDB cache and from
 * the network, in no fixed order, and the controls re-seeded themselves from
 * whichever arrived last. A publish landing mid-edit put the stored value back
 * into the input, so the blur handler saw nothing to save and the text was lost.
 *
 * Staging removes that race rather than working around it. A field the person has
 * touched has an entry here, and an entry always wins over the document, so a late
 * publish can only ever fill in the fields nobody is working on. There is no local
 * copy of the value for a publish to overwrite: `values` is the single place the
 * controls read from.
 */
export function useProfileFieldDraft(options: ProfileFieldDraftOptions): {
  draft: ComputedRef<ProfileFieldDraft>
  isDirty: ComputedRef<boolean>
  isSaving: Ref<boolean>
  save: () => Promise<boolean>
  discard: () => void
} {
  const staged = ref<StagedUpdates>({})
  const isSaving = ref(false)

  const values = computed<ProfileFieldValues>(() => {
    let merged = { ...options.stored() }
    for (let update of Object.values(staged.value)) {
      if (update) applyUpdate(merged, update)
    }
    return merged
  })

  /** Only the fields whose staged value differs from the stored one are written. */
  const changedUpdates = computed<ProfileFieldUpdate[]>(() => {
    let stored = options.stored()
    let merged = values.value
    let updates: ProfileFieldUpdate[] = []
    for (let update of Object.values(staged.value)) {
      if (!update || !isChanged(update, stored)) continue
      updates.push(toWrite(update, merged))
    }
    return updates
  })

  const isDirty = computed(() => changedUpdates.value.length > 0)

  const draft = computed<ProfileFieldDraft>(() => ({
    values: values.value,
    stage,
    reset,
  }))

  function stage(update: ProfileFieldStage) {
    staged.value = { ...staged.value, [update.field]: merge(staged.value[update.field], update) }
  }

  function reset(field: StagedField) {
    let next = { ...staged.value }
    delete next[field]
    staged.value = next
  }

  function discard() {
    staged.value = {}
  }

  /**
   * Writes every changed field, one document call each.
   *
   * Resolves false when a write failed. `ProfileFieldEditor.save` reports the
   * failure itself, so the caller has nothing to add; the staged edits stay put,
   * which keeps what was typed on screen and lets Save be pressed again.
   */
  async function save(): Promise<boolean> {
    let updates = changedUpdates.value
    if (updates.length === 0) return true

    let editor = options.editor()
    if (!editor) return false

    isSaving.value = true
    try {
      for (let update of updates) {
        await editor.save(update)
      }
      // Re-read before dropping the staged values: they are what the canvas is
      // showing, and clearing them first would flash the pre-save value back on
      // screen until the documents caught up.
      await options.onSaved()
      staged.value = {}
      return true
    } catch {
      return false
    } finally {
      isSaving.value = false
    }
  }

  return { draft, isDirty, isSaving, save, discard }
}

/**
 * Folds a new stage into the one already held for that field.
 *
 * Only a name has anything to fold: it is staged one input at a time, so typing a
 * first name and then a last name has to end up with both rather than only the
 * second. Every other field is one control and replaces itself.
 */
function merge(
  previous: ProfileFieldStage | undefined,
  next: ProfileFieldStage,
): ProfileFieldStage {
  if (next.field !== 'full_name' || previous?.field !== 'full_name') return next
  return { ...previous, ...next }
}

/**
 * A staged edit as the write it will become.
 *
 * Only a name needs filling in. It is staged a half at a time and written as a
 * pair, so the half nobody typed is taken from the merged values, where it is
 * whatever the `User` document holds by the time Save is pressed.
 */
function toWrite(update: ProfileFieldStage, values: ProfileFieldValues): ProfileFieldUpdate {
  if (update.field !== 'full_name') return update
  return { field: 'full_name', firstName: values.firstName, lastName: values.lastName }
}

function applyUpdate(values: ProfileFieldValues, update: ProfileFieldStage) {
  if (update.field === 'full_name') {
    if (update.firstName !== undefined) values.firstName = update.firstName
    if (update.lastName !== undefined) values.lastName = update.lastName
    return
  }
  if (update.field === 'cover_image_position') {
    values.cover_image_position = update.value
    return
  }
  values[update.field] = update.value
}

function isChanged(update: ProfileFieldStage, stored: ProfileFieldValues) {
  if (update.field === 'full_name') {
    // An untyped half is not a change: it has no staged value, so there is
    // nothing to compare and nothing of it to write.
    return (
      (update.firstName !== undefined && update.firstName !== stored.firstName) ||
      (update.lastName !== undefined && update.lastName !== stored.lastName)
    )
  }
  if (update.field === 'cover_image_position') {
    return update.value !== stored.cover_image_position
  }
  return update.value !== stored[update.field]
}
