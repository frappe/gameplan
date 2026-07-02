<template>
  <RouterLink :to="linkTo" custom v-slot="{ href, navigate }">
    <a
      :href="href"
      class="group relative block h-[68px] select-none transition-colors duration-150 active:bg-surface-gray-2 sm:h-15 sm:rounded-[10px] sm:hover:bg-surface-gray-1"
      @click="handleRowClick($event, navigate)"
    >
      <div class="flex h-[68px] items-center overflow-hidden px-4 py-2 sm:h-full sm:px-3">
        <div
          class="flex shrink-0 items-center overflow-hidden transition-[width] duration-200 ease-out"
          :style="{ width: selectable ? '32px' : '0px' }"
        >
          <Transition
            enter-active-class="transition-transform duration-75 ease-out"
            leave-active-class="transition-transform duration-75 ease-out"
            enter-from-class="scale-0"
            leave-to-class="scale-0"
          >
            <div
              v-if="selectable"
              class="flex items-center"
              role="checkbox"
              :aria-checked="selected"
              tabindex="0"
              @click.stop="handleSelection"
              @keydown.enter.prevent="handleSelection"
              @keydown.space.prevent="handleSelection"
            >
              <Checkbox :modelValue="selected" />
            </div>
          </Transition>
        </div>
        <div class="flex items-center space-x-3">
          <div class="relative flex">
            <UserAvatarWithHover :user="discussion.owner" size="2xl" />
          </div>
        </div>
        <div class="mx-3 min-w-0 flex-1 sm:ml-4 sm:mr-4">
          <div class="flex min-w-0 items-center">
            <div
              class="overflow-hidden text-ellipsis whitespace-nowrap leading-none"
              :class="discussion.unread ? 'text-ink-gray-8' : 'text-ink-gray-8'"
            >
              <span
                class="overflow-hidden text-ellipsis whitespace-nowrap"
                :class="[
                  discussion.unread
                    ? 'text-lg-semibold sm:text-base-semibold'
                    : 'text-lg sm:text-base',
                ]"
              >
                {{ discussion.title }}
              </span>
            </div>
          </div>
          <div class="mt-1.5 flex min-w-0 items-center justify-between">
            <div
              class="inline-flex items-center overflow-hidden text-ellipsis whitespace-nowrap text-md text-ink-gray-5 sm:text-base"
            >
              <div class="flex items-center min-w-0">
                <div class="text-ink-gray-5">
                  <Tooltip v-if="discussion.closed_at" text="Closed">
                    <span class="lucide-lock size-4 p-[1px] mr-1" />
                  </Tooltip>
                  <Tooltip v-else-if="discussion.last_post_type == 'GP Comment'" text="Comment">
                    <span class="lucide-reply size-4 mr-1" />
                  </Tooltip>
                  <Tooltip v-else-if="discussion.last_post_type == 'GP Poll'" text="Poll">
                    <span class="lucide-align-left size-4 p-[1px] mr-1" />
                  </Tooltip>
                </div>
                <div>
                  <span>
                    {{ useUser(discussion.last_post_by).full_name.trim() }}
                  </span>
                  <span class="inline-flex items-center" v-if="showSpaceName">
                    &nbsp;in {{ discussion.project_title }}
                    <span
                      v-if="isSpacePrivate(discussion.project)"
                      class="lucide-lock h-3 w-3 text-ink-gray-6 ml-0.5"
                    /> </span
                  >:&nbsp;
                </div>
                <div class="truncate">
                  {{ discussion.last_comment_content || discussion.last_poll_title }}
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="ml-auto">
          <Tooltip :text="dayjsLocal(discussion.last_post_at).format('D MMM YYYY [at] h:mm A')">
            <div class="shrink-0 whitespace-nowrap text-sm text-ink-gray-5 text-right">
              {{ relativeTimestamp(discussion.last_post_at || discussion.creation) }}
            </div>
          </Tooltip>
          <div class="mt-1.5 flex items-center justify-end space-x-3">
            <Tooltip text="Ongoing poll" v-if="discussion.ongoing_polls?.length">
              <span class="lucide-bar-chart-2 h-4 w-4 -rotate-90" />
            </Tooltip>
            <Tooltip v-if="discussion.unread">
              <div
                class="bg-amber-600 dark:bg-dark-amber-500 text-white rounded-full h-4 min-w-4 px-1 grid place-content-center text-xs"
              >
                {{ discussion.unread }}
              </div>
              <template #content>
                <div v-if="discussion.comments_count + 1 === discussion.unread">
                  New unread post
                </div>
                <div v-else-if="discussion.comments_count > 0" class="p-0.5">
                  <div>{{ discussion.unread }} unread</div>
                  <div class="text-ink-gray-3 mt-0.5">
                    {{ discussion.comments_count }}
                    {{ discussion.comments_count == 1 ? 'comment' : 'comments' }}
                  </div>
                </div>
              </template>
            </Tooltip>
            <Badge v-else>{{ (discussion.comments_count || 0) + 1 }}</Badge>
          </div>
        </div>
      </div>
      <!-- Separator -->
      <div class="pl-1" v-if="index < total - 1">
        <div class="ml-16 mr-4 h-px border-t transition-opacity group-hover:opacity-0 sm:mr-3" />
      </div>
    </a>
  </RouterLink>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { Tooltip, Badge, dayjsLocal, Checkbox } from 'frappe-ui'
import UserAvatarWithHover from './UserAvatarWithHover.vue'
import { getSpace, useSpace } from '@/data/spaces'
import { Discussion } from '@/data/discussions'
import { relativeTimestamp } from '@/utils'
import { useUser } from '@/data/users'

const props = defineProps<{
  discussion: Discussion
  index: number
  total: number
  showSpaceName: boolean
  selectable?: boolean
  selected?: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle-selection', name: string): void
}>()

const linkTo = computed(() => {
  return {
    name: 'Discussion',
    params: {
      communityId: getSpace(props.discussion.project)?.team,
      spaceId: props.discussion.project,
      postId: props.discussion.name,
      slug: props.discussion.slug,
    },
  }
})

function handleSelection() {
  if (!props.selectable) return
  emit('toggle-selection', props.discussion.name)
}

function handleRowClick(event: MouseEvent, navigate: (event?: MouseEvent) => void) {
  if (props.selectable) {
    event.preventDefault()
    emit('toggle-selection', props.discussion.name)
    return
  }
  navigate(event)
}

function isSpacePrivate(spaceId: string) {
  return useSpace(spaceId).value?.is_private
}
</script>
