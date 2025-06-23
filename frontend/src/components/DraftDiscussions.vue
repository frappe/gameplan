<template>
  <div>
    <EmptyStateBox v-if="drafts.data?.length === 0" class="mx-3">
      <LucideCoffee class="h-7 w-7 text-ink-gray-4" />
      No drafts
    </EmptyStateBox>
    <div v-else>
      <template v-for="(draft, index) in drafts.data" :key="draft.name">
        <router-link
          class="flex items-center py-2 px-3 group relative h-15 rounded-[10px] transition hover:bg-surface-gray-2"
          :to="{ name: 'NewDiscussion', query: { draft: draft.name } }"
        >
          <UserAvatarWithHover :user="draft.owner" size="2xl" />
          <div class="ml-4 flex-1 min-w-0">
            <div class="flex items-center min-w-0">
              <span
                class="overflow-hidden text-ellipsis whitespace-nowrap leading-none text-ink-gray-8 text-base font-medium"
              >
                {{ draft.title }}
              </span>
            </div>
            <div class="flex mt-1.5 items-center min-w-0">
              <div
                class="overflow-hidden text-ellipsis whitespace-nowrap text-base inline-flex items-center text-ink-gray-5"
              >
                <div v-if="draft.project_title" class="inline-flex items-center">
                  <span>{{ draft.project_title }}</span>
                  <LucideLock
                    v-if="isSpacePrivate(draft.project)"
                    class="h-3 w-3 text-ink-gray-6 ml-0.5"
                  />
                  <span>:&nbsp;</span>
                </div>
                <span class="overflow-hidden text-ellipsis whitespace-nowrap">
                  {{ contentPreview(draft.content) }}
                </span>
              </div>
            </div>
          </div>
          <div class="ml-auto shrink-0">
            <Tooltip :text="dayjsLocal(draft.modified).format('D MMM YYYY [at] h:mm A')">
              <div class="shrink-0 whitespace-nowrap text-sm text-ink-gray-5 text-right">
                {{ relativeTimestamp(draft.modified) }}
              </div>
            </Tooltip>
          </div>
        </router-link>
        <div
          class="mx-3 h-px border-t border-outline-gray-modals transition-opacity group-hover:opacity-0"
          v-if="index < (drafts.data?.length || 0) - 1"
        ></div>
      </template>
    </div>
  </div>
</template>
<script setup lang="ts">
import { Tooltip, dayjsLocal } from 'frappe-ui'
import { GPDraft } from '@/types/doctypes'
import { useList } from 'frappe-ui/src/data-fetching'
import UserAvatarWithHover from './UserAvatarWithHover.vue'
import { useSpace } from '@/data/spaces'
import { relativeTimestamp } from '@/utils'

interface Draft extends GPDraft {
  project_title: string
}

let drafts = useList<Draft>({
  doctype: 'GP Draft',
  filters: {
    type: 'Discussion',
  },
  fields: [
    'name',
    'title',
    'content',
    'project',
    'project.title as project_title',
    'creation',
    'modified',
    'owner',
  ],
  orderBy: 'creation desc',
})

function contentPreview(content?: string) {
  if (content) {
    // remove html tags
    return content.replace(/<[^>]*>?/gm, '').slice(0, 100)
  }
}

function isSpacePrivate(spaceId?: string) {
  if (!spaceId) return false
  return useSpace(spaceId).value?.is_private
}
</script>
