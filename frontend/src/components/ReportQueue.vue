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
      class="flex items-center justify-between gap-4 border-b border-outline-gray-2 py-5 text-ink-gray-9"
    >
      <div>
        <p class="text-base-medium">
          {{ item.reference_doctype === 'GP Comment' ? 'Reply' : 'Discussion' }} #{{
            item.reference_name
          }}
        </p>
        <p
          v-if="item.discussion_title"
          class="mt-1 line-clamp-2 break-words text-base text-ink-gray-5"
        >
          {{ item.discussion_title }}
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
  <ModerationDialog
    v-model:open="showReview"
    title="Review reports"
    :busy="resolving"
    :content-key="`${view}-${selectedReport}-${details?.current.version}`"
  >
    <template v-if="details" #sidebar>
      <div class="space-y-5">
        <Select
          v-if="details.reports.length > 1"
          v-model="selectedReport"
          label="Report"
          :options="reportOptions"
          @update:model-value="view = 'current'"
        />
        <section
          v-if="activeReport"
          class="rounded-5 border border-outline-gray-3 bg-surface-gray-2 p-4"
          aria-label="Reporter feedback"
        >
          <p class="text-base-semibold">{{ activeReport.reason }}</p>
          <p class="mt-2 text-base text-ink-gray-7">
            {{
              activeReport.automatic_rule
                ? 'Automatic watched-word rule'
                : useUser(activeReport.owner).full_name
            }}
          </p>
          <time class="mt-1 block text-p-sm text-ink-gray-6">{{
            dayjsLocal(activeReport.creation).format('D MMM YYYY [at] h:mm A')
          }}</time>
          <p class="mt-4 whitespace-pre-wrap break-words text-base text-ink-gray-9">
            {{ activeReport.note || 'No additional note.' }}
          </p>
          <Button
            class="mt-4"
            :loading="evidenceLoading"
            :disabled="resolving"
            @click="loadReview(activeReport.name)"
            >View reported version</Button
          >
        </section>
        <div v-if="reportStart || details.has_more" class="flex gap-2">
          <Button v-if="reportStart" @click="reportPage(-40)">Previous reports</Button>
          <Button v-if="details.has_more" @click="reportPage(40)">More reports</Button>
        </div>
        <template v-if="details.review.status === 'Pending'">
          <Select
            v-model="decision"
            label="Decision"
            :disabled="resolving || evidenceLoading"
            :options="['Dismiss', 'Uphold', 'Hide', 'Delete Spam']"
          />
          <p class="text-p-sm text-ink-gray-6">{{ decisionHelp[decision] }}</p>
          <Textarea
            v-model="note"
            label="Decision note"
            :maxlength="500"
            required
            :disabled="resolving"
          />
        </template>
        <div v-else class="space-y-2 text-base">
          <p class="font-medium">
            {{ details.review.decision }} by {{ useUser(details.review.decided_by).full_name }}
          </p>
          <p class="whitespace-pre-wrap text-ink-gray-7">{{ details.review.decision_note }}</p>
        </div>
      </div>
    </template>
    <template v-if="details">
      <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
        <p class="text-base text-ink-gray-6">
          {{ view === 'reported' ? 'Reported version' : 'Current post' }} ·
          {{ useUser(details.current.owner).full_name }}
        </p>
        <div class="flex gap-2">
          <Button v-if="view === 'reported'" @click="view = 'current'">Current post</Button>
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
      </div>
      <h3 class="mb-5 text-xl-semibold">
        {{ view === 'reported' ? details.evidence?.reported_title : details.current.title }}
      </h3>
      <p v-if="details.polls.length" class="mb-4 text-p-sm text-ink-gray-6">
        Poll previews show the current question and results.
      </p>
      <CommentEditor
        :key="`${view}-${details.current.version}-${details.evidence?.name}`"
        :value="
          view === 'reported' ? details.evidence?.reported_content || '' : details.current.content
        "
        :editable="false"
      />
    </template>
    <p v-else role="status" class="text-base text-ink-gray-6">Loading review…</p>
    <ErrorMessage
      v-if="reviewError"
      class="mt-4"
      :message="extractServerMessage(reviewError) || 'Could not review reports'"
    />
    <template #actions>
      <Button v-if="reviewError" @click="loadReview()">Refresh review</Button>
      <Button :disabled="resolving" @click="showReview = false">Close</Button>
      <Button
        v-if="details?.review.status === 'Pending'"
        variant="solid"
        :loading="resolving"
        :disabled="!note.trim() || !decision || evidenceLoading"
        @click="resolve"
        >Resolve review</Button
      >
    </template>
  </ModerationDialog>
</template>
<script setup lang="ts">
import { computed, provide, ref, watch } from 'vue'
import { Button, ErrorMessage, Select, Textarea, call, dayjsLocal } from 'frappe-ui'
import ModerationDialog from './ModerationDialog.vue'
import CommentEditor from '@/components/editor/CommentEditor.vue'
import { threadPollsKey } from '@/components/PollBlock/poll-draft'
import type { GPPoll } from '@/types/doctypes'
import { useUser } from '@/data/users'
import { reloadDiscussionLists } from '@/data/discussions'
import { extractServerMessage } from '@/utils'
const props = defineProps<{ communityId: string }>()
type Review = {
  name: string
  reference_doctype: string
  reference_name: string
  discussion_title?: string
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
    automatic_rule?: number
  }[]
  evidence: { name: string; reported_title?: string; reported_content: string } | null
  polls: GPPoll[]
  has_more: boolean
}
const status = ref('Pending'),
  start = ref(0),
  hasMore = ref(false),
  loading = ref(false)
const items = ref<Review[]>([]),
  error = ref<unknown>(null)
const selectedReport = ref('')
const view = ref('current')
const evidenceLoading = ref(false)
const activeReport = computed(() =>
  details.value?.reports.find((report) => report.name === selectedReport.value),
)
const reportOptions = computed(
  () =>
    details.value?.reports.map((report) => ({
      label: `${report.reason} · ${useUser(report.owner).full_name}`,
      value: report.name,
    })) || [],
)
const decisionHelp: Record<string, string> = {
  Dismiss: 'No action needed. The post stays visible.',
  Uphold: 'Accept the report and keep the post visible.',
  Hide: 'Hide this post. Moderators can restore it later.',
  'Delete Spam': 'Remove this post as spam. Moderators can restore it later.',
}
const showReview = ref(false),
  details = ref<Details | null>(null),
  reviewError = ref<unknown>(null)
const active = ref(''),
  reportStart = ref(0),
  decision = ref('Dismiss'),
  note = ref(''),
  resolving = ref(false)
provide(threadPollsKey, {
  polls: {
    get data() {
      return details.value?.polls ?? []
    },
    get loading() {
      return !details.value
    },
  },
  space: () => null,
  readOnlyMode: () => true,
})
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
  details.value = null
  selectedReport.value = ''
  view.value = 'current'
  showReview.value = true
  loadReview()
}
let detailRequest = 0
async function loadReview(report = '') {
  const current = ++detailRequest
  evidenceLoading.value = true
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
      selectedReport.value = report || result.reports[0]?.name || ''
      view.value = report ? 'reported' : 'current'
    }
  } catch (e) {
    if (current === detailRequest) reviewError.value = e
  } finally {
    if (current === detailRequest) evidenceLoading.value = false
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
