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
  /** Stored `readme` HTML the editor opens on. */
  text?: string
  /** Rejects when the write fails, so the draft stays open. */
  save: (value: string) => Promise<void>
}>()

const open = defineModel<boolean>('open', { required: true })

const draft = ref('')
const saving = ref(false)

const actions = computed(() => [
  { label: 'Discard', onClick: () => (open.value = false) },
  { label: 'Save', variant: 'solid', loading: saving.value, onClick: saveAbout },
])

watch(open, (isOpen) => {
  if (isOpen) draft.value = props.text || ''
})

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
