<template>
  <Textarea
    :label="spec.title"
    class="w-full"
    :data-profile-panel-field="spec.field"
    :rows="4"
    :maxlength="profileBioLimit"
    :model-value="value"
    :placeholder="spec.emptyPrompt"
    @update:model-value="stageText"
  >
    <template #description>{{ charactersLeft }} characters left</template>
  </Textarea>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Textarea } from 'frappe-ui'
import { profileBioLimit, type ProfileBoundFieldSpec, type ProfileFieldDraft } from '../types'

const props = defineProps<{
  spec: ProfileBoundFieldSpec
  draft: ProfileFieldDraft
}>()

// Straight onto the draft, with no local copy in between. A copy would have to be
// re-seeded from the document, and a document publish landing mid-edit is exactly
// what used to eat what was being typed.
const value = computed(() => props.draft.values.bio)
const charactersLeft = computed(() => profileBioLimit - value.value.length)

function stageText(text: string) {
  // Bio is the only short-text bound field, so the narrowing is a formality that
  // keeps the update union honest.
  if (props.spec.field !== 'bio') return
  props.draft.stage({ field: props.spec.field, value: text })
}
</script>
