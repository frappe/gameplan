<template>
  <div class="space-y-3">
    <TextInput
      label="First name"
      class="w-full"
      data-profile-panel-field="first_name"
      :model-value="draft.values.firstName"
      @update:model-value="stageName($event, draft.values.lastName)"
    />
    <TextInput
      label="Last name"
      class="w-full"
      data-profile-panel-field="last_name"
      :model-value="draft.values.lastName"
      @update:model-value="stageName(draft.values.firstName, $event)"
    />
  </div>
</template>

<script setup lang="ts">
import { TextInput } from 'frappe-ui'
import type { ProfileFieldDraft } from '../types'

const props = defineProps<{ draft: ProfileFieldDraft }>()

// A name is two inputs and one write, so either input stages the pair. Both read
// the draft directly: there is no local copy for a late document publish to
// overwrite, and nothing is written until the page's Save.
function stageName(firstName: string, lastName: string) {
  props.draft.stage({ field: 'full_name', firstName, lastName })
}
</script>
