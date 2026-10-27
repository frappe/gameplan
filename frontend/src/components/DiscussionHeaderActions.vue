<template>
  <DiscussionNotificationBell :state="state" :loading="loading" @select="emit('select', $event)" />
  <Dropdown
    align="end"
    :button="{
      icon: 'lucide-more-horizontal',
      variant: 'ghost',
      label: 'Discussion Options',
    }"
    :options="actions"
  />
</template>

<script setup lang="ts">
import { Dropdown, type DropdownOptions } from 'frappe-ui'
import DiscussionNotificationBell from './DiscussionNotificationBell.vue'
import type { DiscussionNotificationState } from '@/data/notificationPreferences'

defineProps<{
  state: DiscussionNotificationState
  loading?: boolean
  actions: DropdownOptions
}>()

const emit = defineEmits<{ (e: 'select', choice: DiscussionNotificationState): void }>()
</script>
