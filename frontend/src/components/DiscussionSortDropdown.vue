<template>
  <!-- A phone has no room for the sort's label beside the tabs, so it shows an icon. -->
  <Dropdown class="shrink-0" :options="discussionSortMenuOptions" align="end">
    <template #trigger="{ open }">
      <Button
        v-if="isMobile"
        size="md"
        icon="lucide-arrow-up-down text-ink-gray-6"
        :label="`Sort: ${discussionSortLabel}`"
        :active="open"
      />
      <Button v-else :label="discussionSortLabel" icon-right="lucide-chevron-down" :active="open" />
    </template>
  </Dropdown>
</template>

<script setup lang="ts">
import { Button, Dropdown } from 'frappe-ui'
import { discussionSortLabel, discussionSortMenuOptions } from '@/data/discussionSort'
import { useIsMobile } from '@/utils/useIsMobile'

const isMobile = useIsMobile()
</script>
