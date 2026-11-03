<template>
  <div class="text-ink-gray-9">
    <template v-if="canModerate">
      <ModerationSidebar
        v-model="tab"
        :options="[
          { label: 'Approvals', value: 'approvals' },
          { label: 'Reports', value: 'reports' },
          { label: 'Removed content', value: 'removed' },
          { label: 'Community bans', value: 'bans' },
          ...(canManageCommunity(community, useSessionUser())
            ? [{ label: 'Watched words', value: 'words' }]
            : []),
          { label: 'History', value: 'history' },
        ]"
      >
        <template #actions>
          <ApprovalSettings
            v-if="tab === 'approvals' && canManageCommunity(community, useSessionUser())"
            :key="communityId"
            :community-id="communityId"
          />
        </template>
        <ErrorMessage
          v-if="error"
          class="mt-4"
          :message="extractServerMessage(error) || 'Could not load moderation data'"
        />
        <WatchedWords
          v-if="tab === 'words' && canManageCommunity(community, useSessionUser())"
          :community-id="communityId"
        />
        <template v-if="tab === 'removed'">
          <Select
            v-model="doctype"
            class="my-4 max-w-xs"
            aria-label="Content type"
            :options="[
              { label: 'Discussions', value: 'GP Discussion' },
              { label: 'Replies', value: 'GP Comment' },
            ]"
          />
          <div v-for="item in items" :key="item.name" class="border-b border-outline-gray-2 py-5">
            <div class="text-base-medium text-ink-gray-9">{{ item.title }}</div>
            <p class="mt-1 text-base text-ink-gray-5">
              {{ item.spam_removed_at ? 'Spam removed' : 'Hidden' }} ·
              {{ useUser(item.owner).full_name }}
            </p>
            <p class="mt-2 whitespace-pre-wrap text-base text-ink-gray-7">{{ item.reason }}</p>
            <div class="mt-3 flex flex-wrap gap-2">
              <Button @click="preview(item)">Preview</Button>
              <Button
                :route="{
                  name: 'Discussion',
                  params: {
                    communityId,
                    spaceId: item.project,
                    postId: item.discussion,
                    slug: item.slug,
                  },
                }"
                >Open discussion</Button
              >
              <Button @click="restore(item)">Restore</Button>
            </div>
            <div
              v-if="selected === item.name"
              class="mt-3 max-h-96 overflow-y-auto rounded-5 border border-outline-gray-2 bg-surface-gray-1 p-4"
            >
              <CommentEditor :value="previewContent" :editable="false" />
            </div>
          </div>
          <p v-if="!loading && !items.length" class="mt-5 text-base text-ink-gray-5">
            No removed content.
          </p>
          <div class="mt-4 flex gap-2">
            <Button v-if="start > 0" @click="start -= 40">Previous</Button>
            <Button v-if="hasMore" @click="start += 40">Next</Button>
          </div>
        </template>
        <template v-else-if="tab === 'bans'">
          <p class="my-4 text-base text-ink-gray-5">
            Bans block participation in this Community until lifted. Reading and participation
            elsewhere stay available.
          </p>
          <div class="flex items-center gap-2">
            <Combobox
              v-model="targetUser"
              v-model:query="userQuery"
              :open="userPickerOpen"
              :loading="userSearchLoading"
              variant="outline"
              open-on-click
              label="User"
              placeholder="Name or email"
              description="Browse eligible members or type at least 2 characters to search."
              class="min-w-0 flex-1"
              :options="userOptions"
              :filterable="false"
              :empty-text="
                userQuery.trim().length === 1
                  ? 'Type one more character to search.'
                  : 'No eligible members match this search.'
              "
              @update:open="setUserPickerOpen"
            >
              <template #item-prefix="{ item }">
                <Avatar :image="item.image" :label="item.label" size="sm" />
              </template>
            </Combobox>
            <Button :disabled="!targetUser" @click="banUser">Ban from Community</Button>
          </div>
          <div
            v-for="ban in bans"
            :key="ban.user"
            class="flex items-center justify-between gap-3 border-b border-outline-gray-2 py-5"
          >
            <div>
              <div class="text-base-medium text-ink-gray-9">{{ useUser(ban.user).full_name }}</div>
              <p class="mt-1 whitespace-pre-wrap text-base text-ink-gray-5">{{ ban.reason }}</p>
            </div>
            <Button @click="liftBan(ban.user)">Lift ban</Button>
          </div>
          <div class="mt-4 flex gap-2">
            <Button v-if="start" @click="start -= 40">Previous</Button>
            <Button v-if="hasMore" @click="start += 40">Next</Button>
          </div>
          <p v-if="!loading && !bans.length" class="mt-5 text-base text-ink-gray-5">
            No active Community bans.
          </p>
        </template>
        <ApprovalQueue v-if="tab === 'approvals'" :key="communityId" :community-id="communityId" />
        <ReportQueue v-if="tab === 'reports'" :communityId="communityId" />
        <ModerationHistory v-if="tab === 'history'" :communityId="communityId" />
        <p v-if="loading" role="status" class="mt-4 text-base text-ink-gray-5">Loading…</p>
      </ModerationSidebar>
    </template>
    <p v-else class="text-base text-ink-gray-5">Only Community moderators can open this page.</p>
  </div>
</template>

<script setup lang="ts">
import ModerationSidebar from '@/components/ModerationSidebar.vue'
import WatchedWords from '@/components/WatchedWords.vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import ApprovalQueue from '@/components/ApprovalQueue.vue'
import ApprovalSettings from '@/components/ApprovalSettings.vue'
import ReportQueue from '@/components/ReportQueue.vue'
import { useRoute, useRouter } from 'vue-router'
import ModerationHistory from '@/components/ModerationHistory.vue'
import { Avatar, Button, Combobox, Select, ErrorMessage, call, dialog, useDoctype } from 'frappe-ui'
import CommentEditor from '@/components/editor/CommentEditor.vue'
import { useCommunity } from '@/data/communities'
import { useSessionUser, useUser } from '@/data/users'
import { canModerateCommunity, canManageCommunity } from '@/utils/permissions'
import { reloadDiscussionLists, useDiscussion } from '@/data/discussions'
import { extractServerMessage } from '@/utils'

const props = defineProps<{ communityId: string }>()
const community = useCommunity(() => props.communityId)
const canModerate = computed(() => canModerateCommunity(community.value, useSessionUser()))
const route = useRoute()
const router = useRouter()
const tab = computed({
  get: () =>
    ['approvals', 'reports', 'removed', 'bans', 'words', 'history'].includes(
      String(route.query.tab),
    )
      ? String(route.query.tab)
      : 'removed',
  set: (value) => {
    router.replace({ query: { ...route.query, tab: value } })
  },
})
const doctype = ref('GP Discussion')
const discussionType = useDoctype('GP Discussion')
const commentType = useDoctype('GP Comment')
const targetType = () => (doctype.value === 'GP Discussion' ? discussionType : commentType)
const start = ref(0)
const loading = ref(false)
const error = ref<unknown>(null)
type RemovedItem = {
  discussion: string
  project: string
  slug: string
  name: string
  title: string
  owner: string
  reason: string
  spam_removed_at?: string
}
const items = ref<RemovedItem[]>([])
const bans = ref<{ user: string; reason: string }[]>([])
const hasMore = ref(false)
const selected = ref('')
const previewContent = ref('')
const targetUser = ref('')
const userQuery = ref('')
const userPickerOpen = ref(false)
const userSearchLoading = ref(false)
const userHasMore = ref(false)
const userCursor = ref('')
const userOptions = ref<{ label: string; value: string; image: string }[]>([])
let userSearchRequest = 0
let userSearchTimer: ReturnType<typeof setTimeout> | undefined
async function loadBanCandidates(query: string, request: number, after = '') {
  userSearchLoading.value = true
  try {
    const result = await call<{
      items: { name: string; full_name: string; user_image: string }[]
      has_more: boolean
      next_cursor: string
    }>('gameplan.moderation.ban_candidates', {
      community: props.communityId,
      query,
      after,
    })
    if (request !== userSearchRequest || !userPickerOpen.value) return
    const options = result.items.map((user) => ({
      label: user.full_name || user.name,
      value: user.name,
      image: user.user_image,
    }))
    userOptions.value = after ? [...userOptions.value, ...options] : options
    userHasMore.value = result.has_more
    userCursor.value = result.next_cursor
  } catch (e) {
    if (request === userSearchRequest) error.value = e
  } finally {
    if (request === userSearchRequest) userSearchLoading.value = false
  }
}

watch([userQuery, userPickerOpen, () => props.communityId], ([query, open]) => {
  const request = ++userSearchRequest
  clearTimeout(userSearchTimer)
  userSearchLoading.value = false
  if (!open) return

  const term = query.trim()
  userOptions.value = []
  userHasMore.value = false
  userCursor.value = ''
  if (term.length === 1) return

  userSearchTimer = setTimeout(() => loadBanCandidates(term, request), term ? 250 : 0)
})

function setUserPickerOpen(open: boolean) {
  userPickerOpen.value = open
  if (open) {
    targetUser.value = ''
    userQuery.value = ''
  }
}

function loadMoreBanCandidatesOnScroll(event: Event) {
  const viewport = event.target
  if (
    !(viewport instanceof HTMLElement) ||
    !viewport.closest('[data-slot="content"]') ||
    viewport.scrollTop + viewport.clientHeight < viewport.scrollHeight - 24 ||
    !userPickerOpen.value ||
    !userHasMore.value ||
    userSearchLoading.value
  ) {
    return
  }
  loadBanCandidates(userQuery.value.trim(), userSearchRequest, userCursor.value)
}

onMounted(() => document.addEventListener('scroll', loadMoreBanCandidatesOnScroll, true))
onBeforeUnmount(() => document.removeEventListener('scroll', loadMoreBanCandidatesOnScroll, true))

let request = 0
async function load() {
  const current = ++request
  items.value = []
  bans.value = []
  selected.value = ''
  error.value = null
  if (!canModerate.value || ['reports', 'approvals', 'history', 'words'].includes(tab.value)) {
    loading.value = false
    return
  }
  loading.value = true
  try {
    if (tab.value === 'removed') {
      const result = await call<{ items: RemovedItem[]; has_more: boolean }>(
        'gameplan.moderation.removed_content',
        { community: props.communityId, doctype: doctype.value, start: start.value },
      )
      if (current !== request) return
      items.value = result.items
      hasMore.value = result.has_more
    } else {
      const result = await call<typeof bans.value>('gameplan.moderation.community_bans', {
        community: props.communityId,
        start: start.value,
      })
      if (current === request) {
        bans.value = result.slice(0, 40)
        hasMore.value = result.length > 40
      }
    }
  } catch (e) {
    if (current === request) error.value = e
  } finally {
    if (current === request) loading.value = false
  }
}
watch([() => props.communityId, doctype, tab], () => {
  start.value = 0
})
watch([() => props.communityId, doctype, tab, start, canModerate], load, { immediate: true })

async function preview(item: RemovedItem) {
  error.value = null
  try {
    const content = await targetType().runDocMethod.submit({
      name: item.name,
      method: 'get_hidden_content',
    })
    previewContent.value = content
    selected.value = item.name
  } catch (e) {
    error.value = e
  }
}
function restore(item: RemovedItem) {
  dialog.confirm({
    title: 'Restore content',
    message:
      'Make this content visible again? A reply stays unavailable while its discussion is removed.',
    confirmLabel: 'Restore',
    onConfirm: async () => {
      await targetType().runDocMethod.submit({ name: item.name, method: 'restore' })
      reloadDiscussionLists()
      await useDiscussion(String(item.discussion)).reload()
      await load()
    },
  })
}
function banUser() {
  dialog.prompt({
    title: 'Ban from Community',
    message: `${
      useUser(targetUser.value).full_name
    } will lose participation rights here until the ban is lifted.`,
    fields: [{ name: 'reason', label: 'Reason', type: 'textarea', required: true }],
    confirmLabel: 'Ban',
    onConfirm: async ({ values }) => {
      await call('gameplan.community_bans.set_ban', {
        community: props.communityId,
        user: targetUser.value,
        banned: 1,
        reason: values.reason,
      })
      targetUser.value = ''
      await load()
    },
  })
}
function liftBan(user: string) {
  dialog.confirm({
    title: 'Lift Community ban',
    message: `Restore participation rights for ${useUser(user).full_name}?`,
    confirmLabel: 'Lift ban',
    onConfirm: async () => {
      await call('gameplan.community_bans.set_ban', {
        community: props.communityId,
        user,
        banned: 0,
      })
      await load()
    },
  })
}
</script>
