<template>
  <Dialog v-model:open="open" title="About" size="3xl">
    <!-- `ReadmeEditor` floats its Save/Discard buttons over its own top-right
         corner, so the content needs room to start below them. -->
    <ReadmeEditor
      v-if="open"
      v-model:editing="editing"
      class="min-h-[16rem] pt-11"
      :resource="resource"
      fieldname="readme"
      :border="false"
      placeholder="Write about yourself"
    />
  </Dialog>
</template>

<script setup lang="ts">
import { defineAsyncComponent, reactive, ref, watch } from 'vue'
import { Dialog } from 'frappe-ui'

// Only the profile owner ever opens this, and it pulls in the rich-text editor.
const ReadmeEditor = defineAsyncComponent(() => import('@/components/editor/ReadmeEditor.vue'))

const props = defineProps<{
  /** Stored `readme` HTML the editor opens on. */
  text?: string
  /** Rejects when the write fails, so the editor keeps the draft open. */
  save: (value: string) => Promise<void>
}>()

const open = defineModel<boolean>('open', { required: true })

const editing = ref(false)
const draft = reactive({ readme: '' })

/**
 * Adapter that lets the generic `ReadmeEditor` drive the bound `readme` field:
 * the draft lives here and Save routes through the caller, so the write lands on
 * the profile document and the cards re-resolve from it.
 */
const resource = {
  doc: draft,
  setValue: {
    submit: (values: Record<string, string>) => props.save(values.readme),
  },
  reload: () => {
    draft.readme = props.text || ''
  },
}

watch(open, (isOpen) => {
  if (!isOpen) return
  draft.readme = props.text || ''
  editing.value = true
})

// `ReadmeEditor` closes itself on a successful save or a discard; that is the
// dialog's only job here, so it closes with it.
watch(editing, (isEditing) => {
  if (!isEditing) open.value = false
})
</script>
