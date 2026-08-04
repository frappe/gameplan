<template>
  <div class="space-y-3">
    <TextInput
      label="First name"
      class="w-full"
      data-profile-panel-field="first_name"
      :model-value="firstName"
      @update:model-value="firstName = $event"
      @blur="saveName"
      @keydown.enter.prevent="saveName"
    />
    <TextInput
      label="Last name"
      class="w-full"
      data-profile-panel-field="last_name"
      :model-value="lastName"
      @update:model-value="lastName = $event"
      @blur="saveName"
      @keydown.enter.prevent="saveName"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { TextInput } from 'frappe-ui'
import { useBoundFieldSave } from './useBoundFieldSave'
import type { ProfileFieldEditor } from '../types'

const props = defineProps<{ fieldEditor: ProfileFieldEditor }>()

const { saving, commit } = useBoundFieldSave(() => props.fieldEditor)

const firstName = ref('')
const lastName = ref('')

// The stored value only changes once a write lands and the profile reloads, so
// this never clobbers what is being typed.
watch(
  () => [props.fieldEditor.firstName, props.fieldEditor.lastName] as const,
  ([storedFirst, storedLast]) => {
    firstName.value = storedFirst || ''
    lastName.value = storedLast || ''
  },
  { immediate: true },
)

function saveName() {
  if (saving.value) return

  let first = firstName.value.trim()
  let last = lastName.value.trim()
  if (first === props.fieldEditor.firstName && last === props.fieldEditor.lastName) return
  commit({ field: 'full_name', firstName: first, lastName: last })
}
</script>
