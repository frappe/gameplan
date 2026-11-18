<template>
  <!-- A phone has no room for the sort's label beside the tabs, so it shows a "…" menu. It
       also carries "Mark all as read", which desktop keeps in the community and space menus,
       because a phone has no header room for those menus. -->
  <Dropdown class="shrink-0" :options="options" align="end">
    <template #trigger="{ open }">
      <Button
        v-if="isMobile"
        size="md"
        icon="lucide-more-horizontal text-ink-gray-6"
        label="Feed options"
        :active="open"
      />
      <Button v-else :label="discussionSortLabel" icon-right="lucide-chevron-down" :active="open" />
    </template>
  </Dropdown>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, Dropdown, type DropdownOptions } from 'frappe-ui'
import { discussionSortLabel, discussionSortMenuOptions } from '@/data/discussionSort'
import { useIsMobile } from '@/utils/useIsMobile'

const props = defineProps<{
  /** Adds "Mark all as read…" to the phone's menu. */
  markAllAsRead?: () => void
}>()

const isMobile = useIsMobile()

const options = computed<DropdownOptions>(() => {
  const markAllAsRead = props.markAllAsRead
  if (!isMobile.value || !markAllAsRead) return discussionSortMenuOptions.value
  return [
    ...discussionSortMenuOptions.value,
    {
      group: 'Feed',
      hideLabel: true,
      options: [{ label: 'Mark all as read…', icon: 'lucide-check-check', onClick: markAllAsRead }],
    },
  ]
})
</script>
