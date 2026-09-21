<template>
  <!-- Publish as before, plus a chevron that opens the schedule options. On a scheduled
       draft the chevron offers Reschedule / Cancel schedule and the time sits beside it. -->
  <div class="flex items-center gap-2">
    <span
      v-if="scheduledAt"
      class="hidden whitespace-nowrap text-sm text-ink-gray-5 sm:inline"
      :title="`Scheduled for ${scheduledAtLabel}`"
    >
      Scheduled · {{ scheduledAtLabel }}
    </span>
    <div class="flex items-center gap-px">
      <Tooltip
        :text="isDraftLoading ? 'Draft is loading' : 'You cannot publish this draft'"
        :disabled="isComposerEditable"
      >
        <Button
          variant="solid"
          :size="size"
          class="rounded-r-none"
          :loading="publishing"
          :disabled="!isComposerEditable || scheduling"
          @click="publish"
        >
          Publish
        </Button>
      </Tooltip>
      <!-- The menu is portaled next to its trigger so the item rows can fill the panel
           edge to edge: a one-item menu with the stock inset row read as a box in a box. -->
      <div
        ref="menuHost"
        class="[&_[data-slot=group]]:!p-0 [&_[data-slot=item]]:!rounded-6 [&_[data-slot=item-list-row]]:!px-3 [&_[data-slot=item-list-row]]:!py-2"
      >
        <Dropdown :options="options" align="end" :portal-to="menuHost ?? undefined">
          <Button
            variant="solid"
            :size="size"
            class="rounded-l-none"
            icon="lucide-chevron-down"
            label="More publish options"
            :disabled="!isComposerEditable || publishing || scheduling"
          />
        </Dropdown>
      </div>
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
  scheduledAtLabel,
  scheduling,
  scheduleDraft,
  unscheduleDraft,
} = useNewDiscussionContext()

const menuHost = ref<HTMLElement | null>(null)
const showSchedule = ref(false)
const openSchedule = () => (showSchedule.value = true)

const options = computed(() =>
  scheduledAt.value
    ? [
        { label: 'Reschedule', icon: 'lucide-calendar-clock', onClick: openSchedule },
        { label: 'Cancel schedule', icon: 'lucide-calendar-x', onClick: unscheduleDraft },
      ]
    : [{ label: 'Schedule for later', icon: 'lucide-calendar-clock', onClick: openSchedule }],
)

async function onSchedule(localDateTime: string) {
  if (await scheduleDraft(localDateTime)) showSchedule.value = false
}
</script>
