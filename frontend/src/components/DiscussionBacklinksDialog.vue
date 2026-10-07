<template>
  <Dialog title="References" v-model:open="open">
    <div v-if="backlinks.loading && !backlinks.data" class="text-base text-ink-gray-5">Loading…</div>
    <div v-else-if="!backlinks.data?.length" class="text-base text-ink-gray-5">No references yet</div>
    <div v-else class="-mx-2">
      <router-link
        v-for="item in backlinks.data"
        :key="item.comment || item.discussion"
        :to="backlinkRoute(item)"
        class="flex w-full items-center gap-2 rounded-4 px-2 py-1.5 hover:bg-surface-gray-2 focus:outline-none focus-visible:ring focus-visible:ring-outline-gray-3"
        @click="open = false"
      >
        <UserAvatar size="sm" :user="item.owner" />
        <span class="truncate text-base text-ink-gray-8">{{ item.title }}</span>
        <span class="ml-auto shrink-0 pl-3 text-sm text-ink-gray-5">
          {{ fullName(item.owner) }} · {{ dayjsLocal(item.creation).fromNow() }}
        </span>
      </router-link>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { Dialog, dayjsLocal, useCall } from 'frappe-ui'
import UserAvatar from '@/components/UserAvatar.vue'
import { useUser } from '@/data/users'
import { getSpace } from '@/data/spaces'

interface Backlink {
  discussion: string
  comment?: string
  title: string
  project: string
  owner: string
  creation: string
}

const props = defineProps<{ discussion: string | number }>()
const open = defineModel<boolean>('open', { default: false })

const backlinks = useCall<Backlink[]>({
  url: computed(() => `/api/v2/document/GP Discussion/${props.discussion}/method/get_backlinks`),
  immediate: false,
})

watch(open, (isOpen) => {
  if (isOpen) backlinks.submit()
})

function fullName(user: string) {
  return useUser(user).full_name?.trim() || user
}

function backlinkRoute(item: Backlink) {
  return {
    name: 'Discussion',
    params: {
      communityId: getSpace(item.project)?.team,
      spaceId: item.project,
      postId: item.discussion,
    },
    query: item.comment ? { comment: item.comment } : {},
  }
}
</script>
