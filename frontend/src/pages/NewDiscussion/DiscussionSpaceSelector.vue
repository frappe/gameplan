<template>
  <Combobox
    trigger="button"
    :options="spaceOptions"
    v-model="draftData.project"
    placeholder="Select Space"
    :disabled="!isComposerEditable"
    @change="handleSpaceChange"
  >
    <template #item-prefix="{ item }">
      <SpaceIcon :icon="optionIcon(item)" class="size-4 text-ink-gray-6" />
    </template>
  </Combobox>
</template>

<script setup lang="ts">
import { Combobox } from 'frappe-ui'
import SpaceIcon from '@/components/SpaceIcon.vue'
import { useNewDiscussionContext } from './useNewDiscussion'

const { draftData, spaceOptions, isComposerEditable, handleSpaceChange } = useNewDiscussionContext()

function optionIcon(item: unknown) {
  if (!item || typeof item !== 'object' || !('icon' in item)) return null
  return (item as { icon?: string | null }).icon || null
}
</script>
