<template>
  <div class="body-container py-5">
    <div class="mb-5 flex items-center justify-between gap-3">
      <h1 class="text-xl-semibold text-ink-gray-9">Community moderation</h1>
      <Button :route="{ name: 'Discussions', params: { communityId } }">Back to discussions</Button>
    </div>
    <template v-if="canModerate">
      <TabButtons
        v-model="tab"
        :options="[
          { label: 'Removed content', value: 'removed' },
          { label: 'Community bans', value: 'bans' },
          { label: 'Reports', value: 'reports' },
        ]"
      />
      <ErrorMessage
        v-if="error"
        class="mt-4"
        :message="extractServerMessage(error) || 'Could not load moderation data'"
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
        <div v-for="item in items" :key="item.name" class="border-b py-4">
          <div class="text-base-medium text-ink-gray-9">{{ item.title }}</div>
          <p class="mt-1 text-base text-ink-gray-5">
            {{ item.spam_removed_at ? 'Spam removed' : 'Hidden' }} ·
            {{ useUser(item.owner).full_name }}
          </p>
          <p class="mt-2 whitespace-pre-wrap text-base text-ink-gray-7">{{ item.reason }}</p>
          <div class="mt-3 flex gap-2">
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
          <div v-if="selected === item.name" class="mt-3 rounded border p-3">
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
        <div class="flex items-end gap-2">
          <Select v-model="targetUser" label="User" class="min-w-0 flex-1" :options="userOptions" />
          <Button :disabled="!targetUser" @click="banUser">Ban from Community</Button>
        </div>
        <div
          v-for="ban in bans"
          :key="ban.user"
          class="flex items-center justify-between gap-3 border-b py-4"
        >
          <div>
            <div class="text-base-medium text-ink-gray-9">{{ useUser(ban.user).full_name }}</div>
            <p class="mt-1 whitespace-pre-wrap text-base text-ink-gray-5">{{ ban.reason }}</p>
          </div>
          <Button @click="liftBan(ban.user)">Lift ban</Button>
        </div>
        <p v-if="!loading && !bans.length" class="mt-5 text-base text-ink-gray-5">
          No active Community bans.
        </p>
      </template>
      <ReportQueue v-if="tab === 'reports'" :communityId="communityId" />
      <p v-if="loading" role="status" class="mt-4 text-base text-ink-gray-5">Loading…</p>
    </template>
    <p v-else class="text-base text-ink-gray-5">Only Community moderators can open this page.</p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import ReportQueue from '@/components/ReportQueue.vue'
import { Button, Select, TabButtons, ErrorMessage, call, dialog, useDoctype } from 'frappe-ui'
import CommentEditor from '@/components/editor/CommentEditor.vue'
import { useCommunity } from '@/data/communities'
import { users, useSessionUser, useUser } from '@/data/users'
import { canModerateCommunity, isGlobalAdmin } from '@/utils/permissions'
import { reloadDiscussionLists, useDiscussion } from '@/data/discussions'
import { extractServerMessage } from '@/utils'

const props = defineProps<{ communityId: string }>()
const community = useCommunity(() => props.communityId)
const canModerate = computed(() => canModerateCommunity(community.value, useSessionUser()))
const tab = ref('removed')
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
const userOptions = computed(() => [
  { label: 'Choose a user', value: '' },
  ...(users.data || [])
    .filter(
      (user) =>
        !isGlobalAdmin(user) &&
        !community.value?.members.some(
          (member) => member.user === user.name && (member.is_admin || member.is_moderator),
        ),
    )
    .map((user) => ({ label: user.full_name, value: user.name })),
])

let request = 0
async function load() {
  const current = ++request
  items.value = []
  bans.value = []
  selected.value = ''
  error.value = null
  if (!canModerate.value || tab.value === 'reports') {
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
      })
      if (current === request) bans.value = result
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
