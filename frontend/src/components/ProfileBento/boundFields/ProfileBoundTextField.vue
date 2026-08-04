<template>
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
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Textarea } from 'frappe-ui'
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

const draft = ref('')
const charactersLeft = computed(() => profileBioLimit - draft.value.length)

watch(
  () => [props.card.id, props.card.text] as const,
  () => {
    draft.value = props.card.text || ''
  },
  { immediate: true },
)

function saveText() {
  if (saving.value || draft.value === (props.card.text || '')) return
  // Bio is the only short-text bound field, so the narrowing is a formality that
  // keeps the update union honest.
  if (props.spec.field !== 'bio') return
  commit({ field: props.spec.field, value: draft.value })
}
</script>
