<template>
  <!-- The Combobox puts its placeholder on the trigger and the search box alike. A custom
       trigger lets the button say "Select space" while the search box says "Search spaces". -->
  <Combobox
    :options="spaceOptions"
    v-model="selectedSpace"
    placeholder="Search spaces"
    :size="size"
    :disabled="!isComposerEditable"
    @change="handleSpaceChange"
  >
    <template #trigger="{ selectedOption, disabled }">
      <Button :size="size" :disabled="disabled" :class="['!justify-start', $attrs.class]">
        <template #prefix>
          <SpaceIcon
            v-if="selectedOption"
            :icon="optionIcon(selectedOption)"
            class="size-4 text-ink-gray-6"
          />
          <span v-else class="lucide-folder size-4 shrink-0 text-ink-gray-6" aria-hidden="true" />
        </template>
        <span :class="{ 'text-ink-gray-7': !selectedOption && !disabled }">
          {{ selectedOption?.label ?? 'Select space' }}
        </span>
        <template #suffix>
          <span
            class="lucide-chevron-down ml-auto size-4 shrink-0 text-ink-gray-4"
            aria-hidden="true"
          />
        </template>
      </Button>
    </template>
    <template #item-prefix="{ item }">
      <SpaceIcon :icon="optionIcon(item)" class="size-4 text-ink-gray-6" />
    </template>
  </Combobox>
</template>

<script setup lang="ts">
import { Button, Combobox } from 'frappe-ui'
import SpaceIcon from '@/components/SpaceIcon.vue'
import { useNewDiscussionContext } from './useNewDiscussion'

// The class goes on the trigger button: the Combobox drops it when a #trigger slot is used.
defineOptions({ inheritAttrs: false })
withDefaults(defineProps<{ size?: 'sm' | 'md' }>(), { size: 'sm' })

const { selectedSpace, spaceOptions, isComposerEditable, handleSpaceChange } =
  useNewDiscussionContext()

function optionIcon(item: unknown) {
  if (!item || typeof item !== 'object' || !('icon' in item)) return null
  return (item as { icon?: string | null }).icon || null
}
</script>
