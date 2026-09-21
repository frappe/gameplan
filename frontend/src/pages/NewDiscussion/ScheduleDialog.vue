<template>
  <Dialog v-model:open="open" title="Schedule for later">
    <div class="space-y-3">
      <p class="text-p-base text-ink-gray-7">
        The post goes out at this time, in your timezone ({{ timezone }}). Until then it stays in
        Drafts and you can keep editing it.
      </p>
      <DateTimePicker
        v-model="value"
        :min="minimum"
        :clearable="false"
        placeholder="Pick a date and time"
        format="ddd D MMM YYYY, h:mm A"
      />
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
import { Button, DateTimePicker, Dialog, ErrorMessage, dayjsLocal } from 'frappe-ui'
import { useNewDiscussionContext } from './useNewDiscussion'

const props = defineProps<{ initial?: string | null }>()
const open = defineModel<boolean>({ default: false })
const emit = defineEmits<{ (e: 'schedule', localDateTime: string): void }>()

const { scheduling, publishError } = useNewDiscussionContext()

const LOCAL = 'YYYY-MM-DD HH:mm:ss'
const value = ref('')
const error = ref('')
const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
const minimum = computed(() => dayjsLocal().format(LOCAL))

// Rescheduling starts from the time on the draft; a fresh schedule from the next full hour.
watch(open, (isOpen) => {
  if (!isOpen) return
  error.value = ''
  value.value = props.initial
    ? dayjsLocal(props.initial).format(LOCAL)
    : dayjsLocal().add(1, 'hour').startOf('hour').format(LOCAL)
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

// A server-side refusal (title missing, past time) surfaces here rather than on the page.
watch(publishError, (message) => {
  if (open.value && message) error.value = message
})
</script>
