<template>
  <div class="space-y-3">
    <TextInput
      label="First name"
      class="w-full"
      data-profile-panel-field="first_name"
      :model-value="draft.values.firstName"
      @update:model-value="stageFirstName"
    />
    <TextInput
      label="Last name"
      class="w-full"
      data-profile-panel-field="last_name"
      :model-value="draft.values.lastName"
      @update:model-value="stageLastName"
    />
  </div>
</template>

<script setup lang="ts">
import { TextInput } from 'frappe-ui'
import type { ProfileFieldDraft } from '../types'

const props = defineProps<{ draft: ProfileFieldDraft }>()

// A name is two inputs and one write, and each input stages only its own half.
// The pair comes from the `User` document, which is not fetched until the profile
// has said who owns it, so for a moment both halves are empty because they are
// unknown. Staging the pair would pin the half nobody typed to that empty value,
// and Save would write the real one away.
//
// Both inputs read the draft directly: there is no local copy for a late document
// publish to overwrite, and nothing is written until the page's Save.
function stageFirstName(firstName: string) {
  props.draft.stage({ field: 'full_name', firstName })
}

function stageLastName(lastName: string) {
  props.draft.stage({ field: 'full_name', lastName })
}
</script>
