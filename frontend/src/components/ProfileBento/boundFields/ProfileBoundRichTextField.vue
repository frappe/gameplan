<template>
  <!-- Rich text does not fit an aside this narrow, so the panel offers the way
       into a dialog rather than a cramped editor. -->
  <div class="space-y-1.5">
    <FormLabel :label="spec.title" size="md" />
    <Button icon-left="lucide-edit-2" @click="showDialog = true">Edit {{ actionName }}</Button>

    <ProfileAboutDialog
      v-model:open="showDialog"
      :text="draft.values.readme"
      :save="stageText"
      :discard="discardText"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, FormLabel } from 'frappe-ui'
import ProfileAboutDialog from '../ProfileAboutDialog.vue'
import type { ProfileBoundFieldSpec, ProfileFieldDraft } from '../types'

const props = defineProps<{
  spec: ProfileBoundFieldSpec
  draft: ProfileFieldDraft
}>()

const showDialog = ref(false)
const actionName = computed(() => props.spec.title.toLowerCase())

/** The dialog's Save puts the text into the draft; the page's Save writes it. */
function stageText(value: string) {
  if (props.spec.field !== 'readme') return Promise.resolve()
  props.draft.stage({ field: props.spec.field, value })
  return Promise.resolve()
}

/**
 * Discard goes back to the stored text, not to whatever the dialog opened on. An
 * earlier staged edit is an unsaved change like any other, and this is the only
 * control that offers to throw this field's away.
 */
function discardText() {
  props.draft.reset('readme')
}
</script>
