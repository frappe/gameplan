<template>
  <Dialog v-model:open="open" title="About" size="3xl" :actions="actions">
    <ReadmeEditor
      v-if="open"
      v-model="draft"
      max-height="55vh"
      placeholder="Write about yourself"
    />
  </Dialog>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { Dialog } from 'frappe-ui'

// Only the profile owner ever opens this, and it pulls in the rich-text editor.
const ReadmeEditor = defineAsyncComponent(() => import('@/components/editor/ReadmeEditor.vue'))

const props = defineProps<{
  /** `readme` HTML the editor opens on. */
  text?: string
  /** Rejects when the write fails, so the draft stays open. */
  save: (value: string) => Promise<void>
  /**
   * Throws this field's unsaved changes away. Left out where there are none to
   * throw away, and closing is the whole of discarding.
   */
  discard?: () => void
}>()

const open = defineModel<boolean>('open', { required: true })

const draft = ref('')
const saving = ref(false)

const actions = computed(() => [
  { label: 'Discard', onClick: discardAbout },
  { label: 'Save', variant: 'solid', loading: saving.value, onClick: saveAbout },
])

watch(open, (isOpen) => {
  if (isOpen) draft.value = props.text || ''
})

/**
 * Discard is about the field, not about this dialog: it goes back to the text the
 * server holds, which is also what the person sees on the page behind it. Closing
 * on the text the dialog opened with would leave an edit staged that nothing else
 * offers to undo.
 */
function discardAbout() {
  props.discard?.()
  open.value = false
}

async function saveAbout() {
  if (saving.value) return

  saving.value = true
  try {
    await props.save(draft.value)
    open.value = false
  } catch {
    // The caller reports the failure; staying open keeps the draft.
  } finally {
    saving.value = false
  }
}
</script>
