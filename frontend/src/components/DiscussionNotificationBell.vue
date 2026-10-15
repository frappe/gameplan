<template>
  <Dropdown
    :options="options"
    align="end"
    :button="{
      icon: discussionStateIcon[state],
      variant: 'ghost',
      label: `Notifications: ${state}`,
      tooltip: `Notifications: ${state}`,
      loading,
    }"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Dropdown } from 'frappe-ui'
import {
  discussionNotificationOptions,
  discussionStateIcon,
  type DiscussionNotificationChoice,
  type DiscussionNotificationState,
} from '@/data/notificationPreferences'

const props = defineProps<{
  state: DiscussionNotificationState
  loading?: boolean
}>()

const emit = defineEmits<{ (e: 'select', choice: DiscussionNotificationChoice): void }>()

const options = computed(() =>
  discussionNotificationOptions(props.state, (choice) => emit('select', choice)),
)
</script>
