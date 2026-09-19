<template>
  <!-- `:button` rather than a slotted trigger: the trigger is rendered `as-child`, and a
       wrapper such as Tooltip (inheritAttrs: false) swallows the click binding. Button
       carries its own tooltip. -->
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
  /** What the discussion resolves to for this user right now. */
  state: DiscussionNotificationState
  loading?: boolean
}>()

const emit = defineEmits<{ (e: 'select', choice: DiscussionNotificationChoice): void }>()

const options = computed(() =>
  discussionNotificationOptions(props.state, (choice) => emit('select', choice)),
)
</script>
