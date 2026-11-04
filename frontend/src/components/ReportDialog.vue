<template>
  <Dialog v-model:open="open" title="Report content">
    <p class="mb-4 text-base text-ink-gray-5">
      Your report and identity are visible only to authorized moderators.
    </p>
    <Select v-model="reason" label="Reason" :options="reasons" />
    <Textarea
      v-model="note"
      class="mt-3"
      label="Note"
      :required="reason === 'Other'"
      :maxlength="500"
    />
    <ErrorMessage
      v-if="error"
      class="mt-3"
      :message="extractServerMessage(error) || 'Could not submit report'"
    />
    <template #actions>
      <Button
        variant="solid"
        :loading="loading"
        :disabled="!reason || (reason === 'Other' && !note.trim())"
        @click="submit"
        >Submit report</Button
      >
    </template>
  </Dialog>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { Button, Dialog, ErrorMessage, Select, Textarea, call, toast } from 'frappe-ui'
import { extractServerMessage } from '@/utils'
const props = defineProps<{ doctype: string; name: string }>()
const open = defineModel<boolean>('open')
const reason = ref('')
const note = ref('')
const loading = ref(false)
const error = ref<unknown>(null)
const reasons = ['Spam', 'Abuse/inappropriate', 'Off-topic', 'AI-generated', 'Other']
async function submit() {
  loading.value = true
  error.value = null
  try {
    await call('gameplan.reporting.submit', { ...props, reason: reason.value, note: note.value })
    toast.success('Report submitted for moderator review.')
    open.value = false
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
</script>
