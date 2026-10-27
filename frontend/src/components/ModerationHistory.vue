<template>
  <form class="my-4 flex flex-wrap items-end gap-2" @submit.prevent="applyFilters">
    <Select v-model="kind" label="History type" :options="kinds" />
    <TextInput
      v-if="kind !== 'all'"
      v-model="target"
      :label="kind === 'user' ? 'User email' : 'Post ID'"
      :placeholder="kind === 'user' ? 'All users' : 'All posts'"
      class="min-w-0 flex-1"
    />
    <Button type="submit">Apply filters</Button>
  </form>
  <ErrorMessage v-if="error" :message="extractServerMessage(error) || 'Could not load history'" />
  <p v-if="loading" role="status" class="mt-4 text-base text-ink-gray-5">Loading history…</p>
  <template v-else>
    <div v-for="item in items" :key="item.name" class="border-b py-4" data-testid="history-row">
      <div class="flex flex-wrap items-baseline justify-between gap-2">
        <p class="text-base-medium text-ink-gray-9">{{ item.action }} · {{ targetLabel(item) }}</p>
        <time :datetime="item.creation" class="text-p-sm text-ink-gray-5">
          {{ dayjsLocal(item.creation).format('D MMM YYYY [at] h:mm A') }}
        </time>
      </div>
      <p class="mt-1 text-base text-ink-gray-5">By {{ useUser(item.owner).full_name }}</p>
      <p v-if="item.reason" class="mt-2 whitespace-pre-wrap text-base text-ink-gray-7">
        {{ item.reason }}
      </p>
    </div>
    <p v-if="!error && !items.length" class="mt-5 text-base text-ink-gray-5">
      No moderation history.
    </p>
    <div class="mt-4 flex gap-2">
      <Button v-if="start > 0" @click="changePage(-40)">Previous</Button>
      <Button v-if="hasMore" @click="changePage(40)">Next</Button>
    </div>
  </template>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, ErrorMessage, TextInput, Select, call, dayjsLocal } from 'frappe-ui'
import { useUser } from '@/data/users'
import { extractServerMessage } from '@/utils'

const props = defineProps<{ communityId: string }>()
const route = useRoute()
const router = useRouter()
const kinds = [
  { label: 'All actions', value: 'all' },
  { label: 'Discussions', value: 'discussion' },
  { label: 'Replies', value: 'reply' },
  { label: 'User bans', value: 'user' },
]
const kind = ref('all')
const target = ref('')
const start = ref(0)
const loading = ref(false)
const error = ref<unknown>(null)
const hasMore = ref(false)
type HistoryItem = {
  name: string
  action: string
  owner: string
  creation: string
  reason?: string
  discussion?: string
  comment?: string
  user?: string
}
const items = ref<HistoryItem[]>([])
function targetLabel(item: HistoryItem) {
  if (item.comment) return `Reply #${item.comment}`
  if (item.discussion) return `Discussion #${item.discussion}`
  return useUser(item.user).full_name
}
function applyFilters() {
  router.replace({
    query: {
      tab: 'history',
      kind: kind.value,
      target: kind.value === 'all' ? undefined : target.value || undefined,
    },
  })
}
let request = 0
async function load() {
  const current = ++request
  items.value = []
  error.value = null
  loading.value = true
  try {
    const result = await call<{ items: HistoryItem[]; has_more: boolean }>(
      'gameplan.moderation_history.history',
      {
        community: props.communityId,
        kind: route.query.kind || 'all',
        target: route.query.target || '',
        start: start.value,
      },
    )
    if (current !== request) return
    items.value = result.items
    hasMore.value = result.has_more
  } catch (e) {
    if (current === request) error.value = e
  } finally {
    if (current === request) loading.value = false
  }
}
watch(
  [() => props.communityId, () => route.query.kind, () => route.query.target],
  () => {
    kind.value = kinds.some((option) => option.value === route.query.kind)
      ? String(route.query.kind)
      : 'all'
    target.value =
      typeof route.query.target === 'string' && kind.value !== 'all' ? route.query.target : ''
    start.value = 0
    load()
  },
  { immediate: true },
)
function changePage(delta: number) {
  start.value += delta
  load()
}
</script>
