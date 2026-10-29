<template>
  <Dialog v-model:open="open" title="Discussion slow mode" :dismissible="!saving">
    <p class="mb-4 text-base text-ink-gray-6">
      Set the minimum time between each person's reply submissions in this discussion. Community
      moderators and admins are exempt. Pending approval submissions also count.
    </p>
    <Select
      v-model="seconds"
      label="Reply interval"
      :options="slowModeIntervals"
      :disabled="loading || saving"
    />
    <Textarea
      v-model="reason"
      class="mt-3"
      label="Reason"
      required
      :maxlength="500"
      :disabled="saving"
    />
    <ErrorMessage
      v-if="error"
      class="mt-3"
      :message="extractServerMessage(error) || 'Could not update slow mode'"
    />
    <template #actions>
      <Button
        variant="solid"
        :loading="saving"
        :disabled="loading || !loaded || !reason.trim()"
        @click="save"
      >
        Save slow mode
      </Button>
    </template>
  </Dialog>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Button, Dialog, ErrorMessage, Select, Textarea, call, toast } from 'frappe-ui'
import { extractServerMessage } from '@/utils'
import { notifySlowModeChanged, slowModeIntervals, type SlowModeStatus } from '@/data/slowMode'

const props = defineProps<{ discussion: string }>()
const open = defineModel<boolean>('open')
const emit = defineEmits<{ saved: [] }>()
const seconds = ref('0')
const previous = ref(0)
const reason = ref('')
const loading = ref(true)
const loaded = ref(false)
const saving = ref(false)
const error = ref<unknown>(null)
onMounted(async () => {
  try {
    const data = await call<SlowModeStatus>('gameplan.slow_mode.status', {
      discussion: props.discussion,
    })
    seconds.value = String(data.seconds)
    previous.value = data.seconds
    loaded.value = true
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
})
async function save() {
  saving.value = true
  error.value = null
  try {
    await call('gameplan.slow_mode.set_mode', {
      discussion: props.discussion,
      seconds: Number(seconds.value),
      expected_seconds: previous.value,
      reason: reason.value,
    })
    notifySlowModeChanged()
    emit('saved')
    open.value = false
    toast.success('Slow mode updated.')
  } catch (e) {
    error.value = e
  } finally {
    saving.value = false
  }
}
</script>
