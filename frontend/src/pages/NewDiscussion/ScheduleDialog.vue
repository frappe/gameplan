<template>
  <Dialog v-model:open="open" title="Schedule for later">
    <div class="space-y-3">
      <p class="text-p-base text-ink-gray-7">
        The post goes out at this time, in your timezone ({{ timezone }}). Until then it stays in
        Drafts and you can keep editing it.
      </p>
      <div class="grid grid-cols-[1fr_auto] gap-2">
        <DatePicker
          v-model="date"
          :min="today"
          :clearable="false"
          placeholder="Pick a date"
          format="ddd D MMM YYYY"
        />
        <TimePicker
          v-model="time"
          :interval="60"
          :typeable="false"
          placeholder="Time"
          format="h:mm A"
        />
      </div>
      <ErrorMessage :message="error" />
    </div>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button variant="outline" :disabled="scheduling" @click="open = false">Cancel</Button>
        <Button variant="solid" :loading="scheduling" @click="confirm">Schedule</Button>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Button, DatePicker, Dialog, ErrorMessage, TimePicker, dayjsLocal } from 'frappe-ui'
import { useNewDiscussionContext } from './useNewDiscussion'

const props = defineProps<{ initial?: string | null }>()
const open = defineModel<boolean>({ default: false })
const emit = defineEmits<{ (e: 'schedule', localDateTime: string): void }>()

const { scheduling, publishError } = useNewDiscussionContext()

const LOCAL = 'YYYY-MM-DD HH:mm:ss'
const date = ref('')
const time = ref('')
const value = computed(() => (date.value && time.value ? `${date.value} ${time.value}` : ''))
const error = ref('')
const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
const today = computed(() => dayjsLocal().format('YYYY-MM-DD'))

watch(open, (isOpen) => {
  if (!isOpen) return
  error.value = ''
  const start = props.initial
    ? dayjsLocal(props.initial)
    : dayjsLocal().add(1, 'hour').startOf('hour')
  date.value = start.format('YYYY-MM-DD')
  time.value = start.format('HH:mm:ss')
})

function confirm() {
  if (!value.value) {
    error.value = 'Pick a date and time'
    return
  }
  if (!dayjsLocal(value.value).isAfter(dayjsLocal())) {
    error.value = 'Pick a time in the future'
    return
  }
  error.value = ''
  emit('schedule', value.value)
}

watch(publishError, (message) => {
  if (open.value && message) error.value = message
})
</script>
