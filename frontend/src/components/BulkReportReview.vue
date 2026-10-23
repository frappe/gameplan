<template>
  <Dialog v-model:open="open" title="Review selected reports" size="4xl" :dismissible="!running">
    <p class="text-base text-ink-gray-6">
      Check these posts before applying one decision and note to all eligible reviews.
    </p>
    <p v-if="loading" role="status" class="mt-4">Loading previews…</p>
    <ErrorMessage v-if="error" class="mt-3" :message="extractServerMessage(error)" />
    <div v-for="item in items" :key="item.review" class="mt-4 border-t pt-4">
      <div class="flex items-start justify-between gap-3">
        <p class="text-base-medium">{{ item.title || `Review ${item.review}` }}</p>
        <Button v-if="item.version" :disabled="running" @click="inspect(item)">Full review</Button>
      </div>
      <p v-if="item.excerpt" class="mt-2 whitespace-pre-wrap text-base">{{ item.excerpt }}</p>
      <p v-if="item.reasons" class="mt-2 text-base text-ink-gray-5">
        {{ item.reasons.map((reason) => `${reason.reason}: ${reason.count}`).join(' · ') }}
      </p>
      <p v-if="item.outcome" role="status" class="mt-2 text-base-medium">{{ item.outcome }}</p>
      <ErrorMessage v-if="item.error" class="mt-2" :message="item.error" />
    </div>
    <template v-if="!finished">
      <Select
        v-model="decision"
        class="mt-5"
        label="Decision for selected reviews"
        :options="['Dismiss', 'Uphold', 'Hide', 'Delete Spam']"
        :disabled="loading || running"
      />
      <Textarea
        v-model="note"
        class="mt-3"
        label="Shared decision note"
        :maxlength="500"
        :disabled="loading || running"
        required
      />
    </template>
    <p v-if="running || finished" role="status" class="mt-4 text-base">
      {{ processed }} of {{ eligible }} processed · {{ succeeded }} resolved.
    </p>
    <p v-if="finished" class="mt-2 text-base text-ink-gray-6">
      Unresolved items remain in the queue. Select them again to review fresh content before
      retrying.
    </p>
    <template #actions>
      <Button v-if="!running" @click="open = false">{{ finished ? 'Done' : 'Cancel' }}</Button>
      <Button
        v-if="!finished"
        variant="solid"
        :loading="running"
        :disabled="loading || Boolean(error) || !eligible || !note.trim()"
        @click="applyDecision"
        >Resolve {{ eligible }} reviews</Button
      >
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { Button, Dialog, ErrorMessage, Select, Textarea, call } from 'frappe-ui'
import { extractServerMessage } from '@/utils'
import type { Review } from '@/data/reporting'

const props = defineProps<{ communityId: string; reviews: string[] }>()
const emit = defineEmits<{ complete: []; inspect: [review: Review] }>()
const open = defineModel<boolean>('open', { default: false })
type Preview = {
  review: string
  reference_doctype: string
  reference_name: string
  title?: string
  excerpt?: string
  version?: string
  reasons?: { reason: string; count: number }[]
  error?: string
  outcome?: string
}
const items = ref<Preview[]>([])
const loading = ref(false),
  running = ref(false),
  finished = ref(false)
const error = ref<unknown>(null),
  decision = ref('Dismiss'),
  note = ref('')
const eligible = computed(() => items.value.filter((item) => item.version).length)
const processed = computed(() => items.value.filter((item) => item.outcome).length)
const succeeded = computed(() => items.value.filter((item) => item.outcome === 'Resolved').length)
let request = 0
let disposed = false
onBeforeUnmount(() => {
  disposed = true
  request++
})
watch(open, async (value) => {
  const current = ++request
  if (!value) return
  items.value = []
  finished.value = false
  error.value = null
  decision.value = 'Dismiss'
  note.value = ''
  loading.value = true
  try {
    const result = await call<Preview[]>('gameplan.reporting_bulk.preview', {
      community: props.communityId,
      reviews: props.reviews,
    })
    if (current === request) items.value = result
  } catch (e) {
    if (current === request) error.value = e
  } finally {
    if (current === request) loading.value = false
  }
})
function inspect(item: Preview) {
  open.value = false
  emit('inspect', {
    name: item.review,
    reference_doctype: item.reference_doctype,
    reference_name: item.reference_name,
  })
}
async function applyDecision() {
  if (running.value || loading.value || !note.value.trim() || !eligible.value) return
  running.value = true
  const community = props.communityId
  const action = decision.value
  const reason = note.value
  // shortcut: leaving this page stops unsent decisions; queue batches if resume is needed.
  for (const item of items.value.filter((item) => item.version)) {
    if (disposed) break
    try {
      await call('gameplan.reporting.resolve', {
        community,
        review: item.review,
        decision: action,
        note: reason,
        expected_version: item.version,
        require_visible: true,
      })
      item.outcome = 'Resolved'
    } catch (e) {
      item.outcome = 'Not resolved'
      item.error =
        extractServerMessage(e) || 'Could not confirm this decision. Review again before retrying.'
    }
  }
  running.value = false
  finished.value = true
  if (!disposed) emit('complete')
}
</script>
