<template>
  <div ref="textField">
    <Textarea
      :label="spec.title"
      class="w-full"
      :data-profile-panel-field="spec.field"
      :rows="4"
      :maxlength="profileBioLimit"
      :model-value="draft"
      :placeholder="spec.emptyPrompt"
      @update:model-value="draft = $event"
      @blur="saveText"
      @keydown.meta.enter.prevent="saveText"
      @keydown.ctrl.enter.prevent="saveText"
    >
      <template #description>{{ charactersLeft }} characters left</template>
    </Textarea>
  </div>
</template>

<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import { Textarea } from 'frappe-ui'
import { useSyncedField } from '@/utils/useSyncedField'
import { useBoundFieldSave } from './useBoundFieldSave'
import {
  profileBioLimit,
  type ProfileBentoCard,
  type ProfileBoundFieldSpec,
  type ProfileFieldEditor,
} from '../types'

const props = defineProps<{
  spec: ProfileBoundFieldSpec
  card: ProfileBentoCard
  fieldEditor: ProfileFieldEditor
}>()

const { saving, commit } = useBoundFieldSave(() => props.fieldEditor)

const textField = useTemplateRef<HTMLElement>('textField')

// See useSyncedField for why the doc store publishes a document more than once
// and why a plain watcher cannot tell a fresh value from a stale one. The card
// id is part of the identity because one panel edits whichever card is selected.
const draft = useSyncedField({
  source: () => props.card.text,
  identity: () => `${props.fieldEditor.userId}/${props.card.id}`,
  target: textField,
})
const charactersLeft = computed(() => profileBioLimit - draft.value.length)

function saveText() {
  if (saving.value || draft.value === (props.card.text || '')) return
  // Bio is the only short-text bound field, so the narrowing is a formality that
  // keeps the update union honest.
  if (props.spec.field !== 'bio') return
  commit({ field: props.spec.field, value: draft.value })
}
</script>
