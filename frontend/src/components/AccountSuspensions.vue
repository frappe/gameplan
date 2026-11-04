<template>
  <div class="space-y-4">
    <p class="text-base text-ink-gray-6">
      Applies to the entire Frappe site and every installed app. Suspended accounts cannot sign in
      or use API access.
    </p>
    <div class="flex flex-wrap items-end gap-2">
      <Combobox
        v-model="chosen"
        v-model:query="query"
        label="User"
        placeholder="Name or email"
        class="min-w-[12rem] flex-1"
        open-on-click
        :options="options"
        :filterable="false"
        :loading="searching"
        @update:open="pickerOpen = $event"
      >
        <template #item-prefix="{ item }"
          ><Avatar :image="item.image" :label="item.label" size="sm"
        /></template>
      </Combobox>
      <Button :disabled="!chosen" @click="edit({ user: chosen })">Suspend account</Button>
      <Button v-if="chosen" @click="showHistory({ user: chosen })">View history</Button>
    </div>
    <Button
      v-if="pickerOpen && candidateCursor"
      :loading="searching"
      @click="search(candidateCursor)"
      >Load more users</Button
    >
    <ErrorMessage
      v-if="error"
      :message="extractServerMessage(error) || 'Could not load suspensions'"
    />
    <p v-if="loading" role="status" class="text-base text-ink-gray-6">Loading suspensions…</p>
    <div
      v-for="item in items"
      :key="item.user"
      class="flex flex-wrap items-center justify-between gap-3 border-b border-outline-gray-2 py-4"
    >
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2">
          <Avatar :image="item.user_image" :label="item.full_name || item.user" size="sm" /><span
            class="text-base-medium"
            >{{ item.full_name || item.user }}</span
          >
        </div>
        <p class="mt-2 text-base text-ink-gray-6">{{ expiryLabel(item.expires_at) }}</p>
        <p class="mt-2 whitespace-pre-wrap break-words text-base">{{ item.reason }}</p>
      </div>
      <div class="flex gap-2">
        <Button @click="edit(item)">Change</Button
        ><Button @click="edit(item, true)">Lift suspension</Button
        ><Button @click="showHistory(item)">History</Button>
      </div>
    </div>
    <p v-if="!loading && !items.length" class="py-6 text-base text-ink-gray-6">
      No active account suspensions.
    </p>
    <div class="flex gap-2">
      <Button v-if="cursors.length" @click="previous">Previous</Button
      ><Button v-if="nextCursor" @click="next">Next</Button>
    </div>
    <RestrictionDialog
      v-if="selected"
      :key="`${selected.user}-${lifting}`"
      v-model:open="dialogOpen"
      :user="selected"
      :lifting="lifting"
      @saved="saved"
    />
    <Dialog v-model:open="historyOpen" title="Account suspension history">
      <ScrollArea class="h-96" viewport-class="h-96 pr-3">
        <div v-for="row in history" :key="row.name" class="border-b border-outline-gray-2 py-4">
          <p class="text-base-medium">
            {{ row.action }} ·
            {{ row.action === 'Restriction Expired' ? 'System' : useUser(row.owner).full_name }}
          </p>
          <p class="mt-1 text-p-sm text-ink-gray-6">
            {{ dayjsLocal(row.creation).format('D MMM YYYY, h:mm A z') }}
          </p>
          <p class="mt-2 whitespace-pre-wrap text-base">{{ row.reason }}</p>
          <p class="mt-2 text-base text-ink-gray-6">{{ restrictionTransition(row) }}</p>
        </div>
        <Button v-if="historyCursor" @click="loadHistory(historyCursor)">More history</Button>
      </ScrollArea>
    </Dialog>
  </div>
</template>
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  Avatar,
  Button,
  Combobox,
  Dialog,
  ScrollArea,
  ErrorMessage,
  call,
  dayjsLocal,
} from 'frappe-ui'
import RestrictionDialog from './RestrictionDialog.vue'
import { expiryLabel, restrictionTransition, type RestrictionUser } from '@/data/restrictions'
import { extractServerMessage } from '@/utils'
import { useUser } from '@/data/users'
const items = ref<RestrictionUser[]>([])
const loading = ref(false),
  searching = ref(false),
  pickerOpen = ref(false)
const error = ref<unknown>(null),
  chosen = ref(''),
  query = ref('')
const options = ref<{ label: string; value: string; image?: string }[]>([])
const cursor = ref(''),
  nextCursor = ref(''),
  cursors = ref<string[]>([]),
  candidateCursor = ref('')
const selected = ref<RestrictionUser | null>(null),
  lifting = ref(false),
  dialogOpen = ref(false)
const historyOpen = ref(false),
  historyUser = ref(''),
  historyCursor = ref('')
type HistoryItem = {
  name: string
  action: string
  owner: string
  creation: string
  reason?: string
  expires_at?: string
  previous_expires_at?: string
}
type Page<T> = { items: T[]; has_more: boolean; next_cursor: string }
type Candidate = { name: string; full_name: string; user_image?: string }
const history = ref<HistoryItem[]>([])
let searchRequest = 0
let timer: ReturnType<typeof setTimeout>
watch([query, pickerOpen], () => {
  const request = ++searchRequest
  clearTimeout(timer)
  options.value = []
  candidateCursor.value = ''
  if (pickerOpen.value && query.value.trim().length !== 1)
    timer = setTimeout(() => search('', request), query.value ? 250 : 0)
})
async function search(after = '', request = searchRequest) {
  searching.value = true
  try {
    const data = await call<Page<Candidate>>('gameplan.restriction_queries.candidates', {
      query: query.value,
      after,
    })
    if (request !== searchRequest) return
    const result = data.items.map((u) => ({
      label: u.full_name || u.name,
      value: u.name,
      image: u.user_image,
    }))
    options.value = after ? [...options.value, ...result] : result
    candidateCursor.value = data.next_cursor
  } catch (e) {
    if (request === searchRequest) error.value = e
  } finally {
    if (request === searchRequest) searching.value = false
  }
}
async function load() {
  loading.value = true
  try {
    const data = await call<Page<RestrictionUser>>(
      'gameplan.restriction_queries.account_suspensions',
      {
        after: cursor.value,
      },
    )
    items.value = data.items
    nextCursor.value = data.next_cursor
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
function edit(user: RestrictionUser, lift = false) {
  selected.value = user
  lifting.value = lift
  dialogOpen.value = true
}
function next() {
  cursors.value.push(cursor.value)
  cursor.value = nextCursor.value
  load()
}
function previous() {
  cursor.value = cursors.value.pop() || ''
  load()
}
function saved() {
  chosen.value = ''
  selected.value = null
  load()
}
async function showHistory(user: RestrictionUser) {
  historyUser.value = user.user
  history.value = []
  historyOpen.value = true
  await loadHistory()
}
async function loadHistory(before = '') {
  try {
    const data = await call<Page<HistoryItem>>('gameplan.restriction_queries.account_history', {
      user: historyUser.value,
      before,
    })
    history.value = before ? [...history.value, ...data.items] : data.items
    historyCursor.value = data.next_cursor
  } catch (e) {
    error.value = e
  }
}
function moreCandidatesOnScroll(event: Event) {
  const element = event.target
  if (
    !pickerOpen.value ||
    searching.value ||
    !candidateCursor.value ||
    !(element instanceof HTMLElement) ||
    !element.querySelector('[role="option"]')
  )
    return
  if (element.scrollHeight - element.scrollTop - element.clientHeight < 48)
    search(candidateCursor.value)
}
onMounted(() => {
  load()
  document.addEventListener('scroll', moreCandidatesOnScroll, true)
})
onBeforeUnmount(() => {
  clearTimeout(timer)
  searchRequest++
  document.removeEventListener('scroll', moreCandidatesOnScroll, true)
})
</script>
