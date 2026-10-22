<template>
  <Select
    v-model="status"
    class="my-4 max-w-xs"
    label="Review status"
    :options="['Pending', 'Resolved']"
  />
  <ErrorMessage
    v-if="error"
    class="mt-3"
    :message="extractServerMessage(error) || 'Could not load reports'"
  />
  <p v-if="loading" role="status" class="mt-4 text-base text-ink-gray-5">Loading reports…</p>
  <template v-else>
    <div
      v-for="item in items"
      :key="item.name"
      class="flex items-center justify-between gap-3 border-b py-4"
    >
      <div>
        <p class="text-base-medium">
          {{ item.reference_doctype === 'GP Comment' ? 'Reply' : 'Discussion' }} #{{
            item.reference_name
          }}
        </p>
        <p class="mt-1 text-base text-ink-gray-5">
          {{ item.decision || 'Pending review' }} ·
          {{ dayjsLocal(item.creation).format('D MMM YYYY [at] h:mm A') }}
        </p>
      </div>
      <Button @click="openReview(item)">Review</Button>
    </div>
    <p v-if="!items.length && !error" class="mt-5 text-base text-ink-gray-5">
      No {{ status.toLowerCase() }} reports.
    </p>
    <div class="mt-4 flex gap-2">
      <Button v-if="start" @click="changePage(-40)">Previous</Button>
      <Button v-if="hasMore" @click="changePage(40)">Next</Button>
    </div>
  </template>
  <Dialog v-model:open="showReview" title="Review reports" :size="'4xl'">
    <template v-if="details">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <p class="text-base-medium">
          Current post · {{ useUser(details.current.owner).full_name }}
        </p>
        <Button
          :route="{
            name: 'Discussion',
            params: {
              communityId,
              spaceId: details.current.project,
              postId: details.current.discussion,
            },
          }"
          target="_blank"
          >Open discussion</Button
        >
      </div>
      <p v-if="details.current.title" class="mt-2 text-base-medium">{{ details.current.title }}</p>
      <CommentEditor
        :key="details.current.version"
        :value="details.current.content"
        :editable="false"
      />
      <p class="mt-5 text-base-medium">Reported versions</p>
      <div v-for="report in details.reports" :key="report.name" class="mt-3 border-t pt-3">
        <Button variant="ghost" @click="loadReview(report.name)"
          >{{ report.reason }} · {{ useUser(report.owner).full_name }}</Button
        >
        <p class="text-p-sm text-ink-gray-5">
          {{ dayjsLocal(report.creation).format('D MMM YYYY [at] h:mm A') }}
        </p>
        <p class="mt-1 whitespace-pre-wrap text-base">{{ report.note }}</p>
        <template v-if="details.evidence?.name === report.name">
          <p class="mt-2 text-base-medium">{{ details.evidence.reported_title }}</p>
          <CommentEditor :value="details.evidence.reported_content" :editable="false" />
        </template>
      </div>
      <div class="mt-3 flex gap-2">
        <Button v-if="reportStart" @click="reportPage(-40)">Previous reports</Button>
        <Button v-if="details.has_more" @click="reportPage(40)">More reports</Button>
      </div>
      <template v-if="details.review.status === 'Pending'">
        <Select
          v-model="decision"
          class="mt-5"
          label="Decision"
          :options="['Dismiss', 'Uphold', 'Hide', 'Delete Spam']"
        />
        <Textarea v-model="note" class="mt-3" label="Decision note" :maxlength="500" required />
      </template>
      <p v-else class="mt-4 whitespace-pre-wrap text-base">
        {{ details.review.decision }} by {{ useUser(details.review.decided_by).full_name }} ·
        {{ dayjsLocal(details.review.decided_at).format('D MMM YYYY [at] h:mm A') }} ·
        {{ details.review.decision_note }}
      </p>
    </template>
    <ErrorMessage
      v-if="reviewError"
      class="mt-3"
      :message="extractServerMessage(reviewError) || 'Could not review reports'"
    />
    <template #actions>
      <Button v-if="reviewError" @click="loadReview()">Refresh review</Button>
      <Button
        v-if="details?.review.status === 'Pending'"
        variant="solid"
        :loading="resolving"
        :disabled="!note.trim() || !decision"
        @click="resolve"
        >Resolve review</Button
      >
    </template>
  </Dialog>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue'
import { Button, Dialog, ErrorMessage, Select, Textarea, call, dayjsLocal } from 'frappe-ui'
import CommentEditor from '@/components/editor/CommentEditor.vue'
import { useUser } from '@/data/users'
import { reloadDiscussionLists } from '@/data/discussions'
import { extractServerMessage } from '@/utils'
const props = defineProps<{ communityId: string }>()
type Review = {
  name: string
  reference_doctype: string
  reference_name: string
  creation: string
  decision?: string
}
type Details = {
  review: {
    status: string
    decision?: string
    decision_note?: string
    decided_by?: string
    decided_at?: string
  }
  current: {
    title?: string
    content: string
    version: string
    owner: string
    discussion: string
    project: string
  }
  reports: {
    name: string
    owner: string
    creation: string
    reason: string
    note: string
  }[]
  evidence: { name: string; reported_title?: string; reported_content: string } | null
  has_more: boolean
}
const status = ref('Pending'),
  start = ref(0),
  hasMore = ref(false),
  loading = ref(false)
const items = ref<Review[]>([]),
  error = ref<unknown>(null)
const showReview = ref(false),
  details = ref<Details | null>(null),
  reviewError = ref<unknown>(null)
const active = ref(''),
  reportStart = ref(0),
  decision = ref('Dismiss'),
  note = ref(''),
  resolving = ref(false)
let request = 0
async function load() {
  const current = ++request
  items.value = []
  error.value = null
  loading.value = true
  try {
    const result = await call<{ items: Review[]; has_more: boolean }>('gameplan.reporting.queue', {
      community: props.communityId,
      status: status.value,
      start: start.value,
    })
    if (current === request) {
      items.value = result.items
      hasMore.value = result.has_more
    }
  } catch (e) {
    if (current === request) error.value = e
  } finally {
    if (current === request) loading.value = false
  }
}
watch(
  [() => props.communityId, status],
  () => {
    start.value = 0
    showReview.value = false
    load()
  },
  { immediate: true },
)
function changePage(delta: number) {
  start.value += delta
  load()
}
function openReview(item: Review) {
  active.value = item.name
  note.value = ''
  decision.value = 'Dismiss'
  reportStart.value = 0
  showReview.value = true
  loadReview()
}
let detailRequest = 0
async function loadReview(report = '') {
  const current = ++detailRequest
  details.value = null
  reviewError.value = null
  try {
    const result = await call<Details>('gameplan.reporting.detail', {
      community: props.communityId,
      review: active.value,
      start: reportStart.value,
      report,
    })
    if (current === detailRequest) {
      details.value = result
    }
  } catch (e) {
    if (current === detailRequest) reviewError.value = e
  }
}
function reportPage(delta: number) {
  reportStart.value += delta
  loadReview()
}
async function resolve() {
  if (!details.value) return
  resolving.value = true
  reviewError.value = null
  try {
    await call('gameplan.reporting.resolve', {
      community: props.communityId,
      review: active.value,
      decision: decision.value,
      note: note.value,
      expected_version: details.value.current.version,
    })
    showReview.value = false
    reloadDiscussionLists()
    await load()
  } catch (e) {
    reviewError.value = e
  } finally {
    resolving.value = false
  }
}
</script>
