<template>
  <div class="flex items-center">
    <Tooltip :text="blockedReason">
      <!-- Fixed width, so the spinner does not push the space picker aside. -->
      <Button
        variant="solid"
        :size="size"
        class="min-w-[5.75rem] rounded-r-none"
        :loading="publishing"
        :disabled="Boolean(blockedReason) || scheduling"
        @click="publish"
      >
        Publish
      </Button>
    </Tooltip>
    <div
      ref="menuHost"
      class="flex [&_[data-slot=group]]:!p-0 [&_[data-slot=item]]:!rounded-6 [&_[data-slot=item-list-row]]:!px-3 [&_[data-slot=item-list-row]]:!py-2"
    >
      <!-- While a request is out the chevron stays solid, like the Publish half, and
           ignores clicks instead of turning grey. -->
      <Dropdown
        :options="options"
        align="end"
        :portal-to="menuHost ?? undefined"
        :disabled="menuDisabled"
      >
        <Button
          variant="solid"
          :size="size"
          class="rounded-l-none"
          :class="{
            '!bg-surface-gray-2 !text-ink-gray-4 hover:!bg-surface-gray-3':
              blockedReason && !menuDisabled,
            'pointer-events-none': busy,
          }"
          icon="lucide-chevron-down"
          label="More publish options"
          :disabled="menuDisabled"
          :tabindex="busy ? -1 : undefined"
          :aria-disabled="busy || undefined"
        />
      </Dropdown>
    </div>
  </div>

  <ScheduleDialog v-model="showSchedule" :initial="scheduledAt" @schedule="onSchedule" />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, Dropdown, Tooltip } from 'frappe-ui'
import { useNewDiscussionContext } from './useNewDiscussion'
import ScheduleDialog from './ScheduleDialog.vue'

withDefaults(defineProps<{ size?: 'sm' | 'md' }>(), { size: 'sm' })

const {
  isDraftLoading,
  isComposerEditable,
  publish,
  publishing,
  scheduledAt,
  scheduling,
  scheduleDraft,
  unscheduleDraft,
  sessionUser,
  author,
  deleteDraft,
  canPublish,
} = useNewDiscussionContext()

const blockedReason = computed(() => {
  if (isDraftLoading.value) return 'Draft is loading'
  if (!isComposerEditable.value) return 'You cannot publish this draft'
  if (!canPublish.value) return 'Add a title and pick a Space to publish'
  return ''
})

const busy = computed(() => publishing.value || scheduling.value)
const menuDisabled = computed(() => isDraftLoading.value || !isComposerEditable.value)

const menuHost = ref<HTMLElement | null>(null)
const showSchedule = ref(false)
const openSchedule = () => (showSchedule.value = true)

const options = computed(() => {
  const items = scheduledAt.value
    ? [
        {
          label: 'Reschedule',
          icon: 'lucide-calendar-clock',
          onClick: openSchedule,
          disabled: !canPublish.value,
        },
        { label: 'Cancel schedule', icon: 'lucide-calendar-x', onClick: unscheduleDraft },
      ]
    : [
        {
          label: 'Schedule for later',
          icon: 'lucide-calendar-clock',
          onClick: openSchedule,
          disabled: !canPublish.value,
        },
      ]

  if (author.value?.name === sessionUser.name) {
    items.push({ label: 'Delete draft', icon: 'lucide-trash-2', onClick: deleteDraft })
  }

  return items
})

async function onSchedule(localDateTime: string) {
  if (await scheduleDraft(localDateTime)) showSchedule.value = false
}
</script>
