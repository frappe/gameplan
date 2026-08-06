import { computed, ref, toValue, watch, type MaybeRefOrGetter, type Ref } from 'vue'
import { useFocusWithin } from '@vueuse/core'

export interface SyncedFieldOptions {
  /** Value the document currently holds for this field. */
  source: MaybeRefOrGetter<string | null | undefined>
  /** Identity of the document `source` is read from, usually its `name`. */
  identity: MaybeRefOrGetter<string | null | undefined>
  /**
   * Element wrapping the input. Focus anywhere inside it counts as engagement, so
   * the value under the cursor never changes while someone is in the field. Leave
   * it out to rely on edits alone.
   */
  target?: MaybeRefOrGetter<HTMLElement | null | undefined>
}

/**
 * A local ref for an input, kept in step with a document field until the person
 * starts working on that field.
 *
 * frappe-ui's doc store publishes the same document more than once, asynchronously
 * and in no fixed order: one publish comes from the IndexedDB cache, another from
 * the network response. Neither of the obvious approaches works. Copying the
 * document into the input on every publish eats what is being typed. Copying it
 * only on the first publish is worse: when the stale cached copy wins the race its
 * value sticks, the network response is ignored, and saving writes the old text
 * back over a newer one.
 *
 * So the ref keeps following the document until the field is engaged, and stops
 * for good after that. Engaged means focused or edited. Edited is the part that
 * matters, because someone can type and then tab away before a late publish lands.
 * A new `identity` is a different document, which clears the engagement and seeds
 * the field again.
 */
export function useSyncedField(options: SyncedFieldOptions): Ref<string> {
  const current = ref('')
  const edited = ref(false)
  const { focused } = useFocusWithin(computed(() => toValue(options.target) ?? null))

  const value = computed({
    get: () => current.value,
    // Only the sync below writes to `current` directly, so every write that arrives
    // here is the person editing.
    set: (next: string) => {
      edited.value = true
      current.value = next
    },
  })

  let syncedIdentity: string | null = null

  watch(
    // `focused` is tracked to re-run the sync on blur: a publish dropped while the
    // field held focus has to be picked up once the person leaves it untouched.
    () => [toValue(options.identity), toValue(options.source), focused.value] as const,
    ([identity, source]) => {
      if (!identity) return

      if (identity !== syncedIdentity) {
        syncedIdentity = identity
        edited.value = false
      } else if (edited.value || focused.value) {
        return
      }

      current.value = source || ''
    },
    { immediate: true },
  )

  return value
}
