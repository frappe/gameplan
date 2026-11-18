<template>
  <PanelHeader title="General" />

  <PanelBody>
    <div class="space-y-11 pt-6">
      <section>
        <div class="divide-y divide-outline-gray-1">
          <SettingsRow
            title="Tasks and Pages"
            description="Show Tasks and Pages in every space and in the menus. Tasks and Pages are deprecated and will be removed soon."
          >
            <Switch v-model="enabled" :disabled="saving || readOnlyMode" />
          </SettingsRow>
        </div>
      </section>
    </div>
  </PanelBody>
</template>

<script setup lang="ts">
// Declared so the parent's @close-dialog isn't treated as a failed attribute
// fallthrough (this component renders a fragment); it simply isn't emitted here.
defineEmits<{ (e: 'close-dialog'): void }>()
import { computed, ref } from 'vue'
import { SettingsRow, Switch, toast } from 'frappe-ui'
import PanelHeader from './PanelHeader.vue'
import PanelBody from './PanelBody.vue'
import { readOnlyMode } from '@/data/readOnlyMode'
import { setTasksAndPagesEnabled, tasksAndPagesEnabled } from '@/data/tasksAndPages'
import { errorText } from '@/utils'

const saving = ref(false)

const enabled = computed({
  get: () => tasksAndPagesEnabled.value,
  set: save,
})

async function save(value: boolean) {
  if (saving.value || value === tasksAndPagesEnabled.value) return
  saving.value = true
  try {
    await setTasksAndPagesEnabled(value)
  } catch (error) {
    toast.error(errorText(error, 'Could not save the setting.'))
  } finally {
    saving.value = false
  }
}
</script>
