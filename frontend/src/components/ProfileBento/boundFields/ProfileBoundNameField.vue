<template>
  <div class="space-y-3">
    <div ref="firstNameField">
      <TextInput
        label="First name"
        class="w-full"
        data-profile-panel-field="first_name"
        :model-value="firstName"
        @update:model-value="firstName = $event"
        @blur="saveName"
        @keydown.enter.prevent="saveName"
      />
    </div>
    <div ref="lastNameField">
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
  </div>
</template>

<script setup lang="ts">
import { useTemplateRef } from 'vue'
import { TextInput } from 'frappe-ui'
import { useBoundFieldSave } from './useBoundFieldSave'
import { useSyncedField } from '@/utils/useSyncedField'
import type { ProfileFieldEditor } from '../types'

const props = defineProps<{ fieldEditor: ProfileFieldEditor }>()

const { saving, commit } = useBoundFieldSave(() => props.fieldEditor)

const firstNameField = useTemplateRef<HTMLElement>('firstNameField')
const lastNameField = useTemplateRef<HTMLElement>('lastNameField')

// See useSyncedField for why the doc store publishes a document more than once
// and why a plain watcher cannot tell a fresh value from a stale one.
const firstName = useSyncedField({
  source: () => props.fieldEditor.firstName,
  identity: () => props.fieldEditor.userId,
  target: firstNameField,
})
const lastName = useSyncedField({
  source: () => props.fieldEditor.lastName,
  identity: () => props.fieldEditor.userId,
  target: lastNameField,
})

function saveName() {
  if (saving.value) return

  let first = firstName.value.trim()
  let last = lastName.value.trim()
  if (first === props.fieldEditor.firstName && last === props.fieldEditor.lastName) return
  commit({ field: 'full_name', firstName: first, lastName: last })
}
</script>
