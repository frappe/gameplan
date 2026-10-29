<template>
  <Button @click="show">Approval settings</Button>
  <Dialog v-model:open="open" title="Community post approval" :dismissible="!saving">
    <p class="mb-4 text-base text-ink-gray-6">
      Review new contributors' discussions and replies before publication. Community staff are
      exempt. Existing published contributions count toward the threshold.
    </p>
    <Checkbox
      v-model="enabled"
      label="Require approval for new contributors"
      :disabled="loading || saving"
    />
    <TextInput
      v-if="enabled"
      v-model="count"
      class="mt-4"
      label="Accepted contributions needed to post freely"
      type="number"
      :min="1"
      :max="100"
      :disabled="loading || saving"
    />
    <p class="mt-3 text-base text-ink-gray-5">
      Changes affect future submissions. Existing pending submissions still need a decision.
    </p>
    <ErrorMessage
      v-if="error"
      class="mt-3"
      :message="extractServerMessage(error) || 'Could not update approval settings'"
    />
    <template #actions
      ><Button
        variant="solid"
        :disabled="
          loading ||
          !loaded ||
          (enabled &&
            (!Number.isInteger(Number(count)) || Number(count) < 1 || Number(count) > 100))
        "
        :loading="saving"
        @click="save"
        >Save approval policy</Button
      ></template
    >
  </Dialog>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { Button, Checkbox, Dialog, ErrorMessage, TextInput, call, toast } from 'frappe-ui'
import { extractServerMessage } from '@/utils'
const props = defineProps<{ communityId: string }>()
const loaded = ref(false)
const open = ref(false),
  enabled = ref(false),
  count = ref('3'),
  loading = ref(false),
  saving = ref(false),
  error = ref<unknown>(null)
async function show() {
  open.value = true
  error.value = null
  loading.value = true
  loaded.value = false
  try {
    const value = await call<number>('gameplan.approval_policy.get_policy', {
      community: props.communityId,
    })
    loaded.value = true
    enabled.value = value > 0
    count.value = String(value || 3)
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
async function save() {
  saving.value = true
  error.value = null
  try {
    await call('gameplan.approval_policy.set_policy', {
      community: props.communityId,
      count: enabled.value ? Number(count.value) : 0,
    })
    open.value = false
    toast.success('Approval policy saved.')
  } catch (e) {
    error.value = e
  } finally {
    saving.value = false
  }
}
</script>
