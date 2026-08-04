<template>
  <!-- Rich text does not fit an aside this narrow, so the panel offers the way
       into a dialog rather than a cramped editor. -->
  <div class="space-y-1.5">
    <FormLabel :label="spec.title" size="md" />
    <Button icon-left="lucide-edit-2" @click="showDialog = true">Edit {{ actionName }}</Button>

    <ProfileAboutDialog v-model:open="showDialog" :text="card.text" :save="saveText" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, FormLabel } from 'frappe-ui'
import ProfileAboutDialog from '../ProfileAboutDialog.vue'
import { useBoundFieldSave } from './useBoundFieldSave'
import type { ProfileBentoCard, ProfileBoundFieldSpec, ProfileFieldEditor } from '../types'

const props = defineProps<{
  spec: ProfileBoundFieldSpec
  card: ProfileBentoCard
  fieldEditor: ProfileFieldEditor
}>()

const { save } = useBoundFieldSave(() => props.fieldEditor)

const showDialog = ref(false)
const actionName = computed(() => props.spec.title.toLowerCase())

/**
 * The dialog handles its own error state, so this hands back the rejection
 * rather than swallowing it the way the inline controls do.
 */
function saveText(value: string) {
  if (props.spec.field !== 'readme') return Promise.resolve()
  return save({ field: props.spec.field, value })
}
</script>
