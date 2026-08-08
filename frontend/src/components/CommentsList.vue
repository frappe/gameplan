<template>
  <div class="flex flex-col">
    <div
      v-if="comments.data == null"
      class="flex animate-pulse items-start space-x-3 px-2 py-4 text-base"
    >
      <div class="h-8 w-8 rounded-full bg-surface-gray-3"></div>
      <div>
        <div class="flex h-8 flex-col justify-center">
          <div class="h-2 w-40 bg-surface-gray-3"></div>
        </div>
        <div class="flex flex-col gap-2">
          <div v-for="i in 4">
            <div
              class="h-2 bg-surface-gray-3"
              :style="{ width: `${Math.max(Math.random() * 800, 600)}px` }"
            ></div>
          </div>
        </div>
      </div>
    </div>
    <div class="px-1">
      <template v-for="(item, i) in timelineItems" :key="item.doctype + item.name">
        <div
          v-if="newMessagesFrom && newMessagesFrom == item.name"
          class="relative my-4"
          role="separator"
        >
          <div class="border-b border-outline-gray-3"></div>
          <span
            class="absolute -top-2 left-1/2 -translate-x-1/2 bg-surface-base px-2 text-sm-medium text-ink-gray-7"
          >
            New comments
          </span>
        </div>
        <Comment
          v-if="item.doctype == 'GP Comment'"
          :class="{
            'pt-14 sm:pt-0': needsMobileCommentGap(timelineItems, i),
          }"
          :ref="($comment) => setItemRef($comment, item)"
          :comment="item"
          :space="space"
          :highlight="highlightedItem == item"
          :readOnlyMode="readOnlyMode"
          :comments="comments"
        />
        <Activity class="my-5" v-else-if="item.doctype == 'GP Activity'" :activity="item" />
      </template>
    </div>

    <div v-if="!readOnlyMode && !disableNewComment" class="px-1 pb-4 pt-12" ref="addComment">
      <div
        class="flex items-start"
        :class="!showCommentBox ? 'cursor-pointer' : ''"
        @click="openCommentBoxFromRow"
      >
        <div class="mr-3 hidden h-8 items-center sm:flex">
          <UserAvatar :user="$user().name" size="md" />
        </div>
        <div class="relative w-full" v-show="!showCommentBox">
          <button
            class="flex w-full items-center rounded-md border px-2 py-2 text-left text-base text-ink-gray-5 hover:border-outline-gray-3"
            @click.stop="openCommentBox"
          >
            Add a comment
          </button>
        </div>
        <div
          v-show="showCommentBox"
          class="w-full rounded-lg border bg-surface-base p-4 focus-within:border-outline-gray-3"
          @keydown.ctrl.enter.capture.stop="submitComment"
          @keydown.meta.enter.capture.stop="submitComment"
        >
          <div class="mb-4 flex items-center sm:hidden">
            <UserAvatar :user="$user().name" size="sm" />
            <span class="ml-2 text-base-medium text-ink-gray-8">
              {{ $user().full_name }}
            </span>
          </div>
          <!-- Bounded: this composer is pinned under the comment list, so it scrolls
               internally past 50vh rather than pushing the task's comments off screen. -->
          <CommentEditor
            ref="newCommentEditor"
            max-height="50vh"
            :value="draftData.content"
            @change="onNewCommentChange"
            :submitButtonProps="{
              variant: 'solid',
              onClick: submitComment,
              loading: comments.insert.loading,
              disabled: commentEmpty,
            }"
            :discardButtonProps="{
              onClick: discardComment,
            }"
            :editable="showCommentBox"
            placeholder="Add a comment"
          />
          <ErrorMessage :message="comments.insert.error" />
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, nextTick, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ErrorMessage, useList } from 'frappe-ui'
import CommentEditor from '@/components/editor/CommentEditor.vue'
import Comment from './Comment.vue'
import Activity from './Activity.vue'
import UserAvatar from './UserAvatar.vue'
import { getScrollContainer } from 'frappe-ui'
import { needsMobileCommentGap } from '@/utils/commentTimeline'
import { dialog } from 'frappe-ui'
import { subscribeToDoc, useSocket, type NewActivityEvent } from '@/socket'
import { GPActivity, GPComment } from '@/types/doctypes'
import type { Space } from '@/data/spaces'
import { useDraftSync } from '@/data/useDraftSync'
import { onReconnect } from '@/data/online'

interface Props {
  doctype: string
  name: string
  // Space the thread belongs to, for community-admin delete moderation.
  space?: Space | null
  newCommentsFrom?: string
  readOnlyMode?: boolean
  disableNewComment?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  readOnlyMode: false,
  disableNewComment: false,
})

const router = useRouter()
const route = useRoute()
const socket = useSocket()

const showCommentBox = ref(false)

// Auto-saved draft for the new-comment composer, keyed to this task. Survives reloads
// and restores across tabs. One draft per (user, task).
const draft = useDraftSync({
  identity: () => ({
    type: 'Comment',
    mode: 'New',
    referenceDoctype: props.doctype,
    referenceName: props.name,
  }),
  initialPayload: () => ({ content: '' }),
})
const draftData = draft.data

const newMessagesFrom = ref(props.newCommentsFrom)
const highlightedItem = ref(null)
const newCommentEditor = ref(null)

const comments = useList<
  Pick<
    GPComment,
    | 'name'
    | 'content'
    | 'owner'
    | 'creation'
    | 'modified'
    | 'edited_at'
    | 'deleted_at'
    | 'reactions'
  >
>({
  doctype: 'GP Comment',
  cacheKey: ['Comments', props.doctype, props.name],
  staleOnError: true,
  fields: [
    'name',
    'content',
    'owner',
    'creation',
    'modified',
    'edited_at',
    'deleted_at',
    { reactions: ['name', 'user', 'emoji'] },
  ],
  transform(data) {
    return data.map((d) => ({ ...d, name: d.name.toString(), doctype: 'GP Comment' }))
  },
  filters: {
    reference_doctype: props.doctype,
    reference_name: props.name,
  },
  orderBy: 'creation asc',
  limit: 99999,
  onSuccess() {
    if (route.query.comment) {
      let comment = comments.data?.find((c) => c.name === route.query.comment)
      scrollToItem(comment)
    } else if (!route.query.fromSearch && comments.data?.length > 0) {
      scrollToEnd()
    }
  },
})

interface Activity extends Pick<GPActivity, 'name' | 'user' | 'action' | 'creation'> {
  data: {
    field?: string
    field_label?: string
    old_value?: string
    new_value?: string
  }
}

const activities = useList<Activity>({
  doctype: 'GP Activity',
  cacheKey: ['Activities', props.doctype, props.name],
  staleOnError: true,
  fields: ['name', 'user', 'action', 'data', 'creation'],
  filters: {
    reference_doctype: props.doctype,
    reference_name: props.name,
  },
  orderBy: 'creation asc',
  limit: 99999,
  transform(activities) {
    return activities.map((activity) => ({
      ...activity,
      doctype: 'GP Activity',
      data: activity.data ? JSON.parse(activity.data as string) : null,
    }))
  },
})

// US5 (seamless recovery): mirrors the same reconnect reload in CommentsArea.vue
// (discussion comments) for this task's comment/activity timeline.
const unregisterReconnect = onReconnect(() => {
  comments.reload()
  activities.reload()
})
onUnmounted(unregisterReconnect)

// Computed
type GroupedActivity = {
  doctype: 'GP Activity'
  name: string
  action: string
  user: string
  creation: string
  data: any
  updates?: { creation: string; data: any }[]
}

const groupedActivities = computed(() => {
  if (!activities.data?.length) return []

  const grouped: GroupedActivity[] = []
  const activityMap = new Map<string, GroupedActivity>()

  const sortedActivities = [...activities.data].sort(
    (a, b) => new Date(a.creation).getTime() - new Date(b.creation).getTime(),
  )

  sortedActivities.forEach((activity) => {
    // Skip if required properties are missing
    if (!activity?.action || !activity?.user) return

    // Only group description changes
    if (activity.action === 'Task Value Changed' && activity.data?.field === 'description') {
      const key = `${activity.action}-${activity.user}-description`

      if (activityMap.has(key)) {
        const existing = activityMap.get(key)!
        if (!existing.updates) existing.updates = []

        existing.updates.push({
          creation: activity.creation,
          data: activity.data,
        })
        // Keep the most recent creation date and data
        if (new Date(activity.creation) > new Date(existing.creation)) {
          existing.creation = activity.creation
          existing.data = activity.data
        }
      } else {
        const newGroup: GroupedActivity = {
          doctype: 'GP Activity',
          name: activity.name,
          action: activity.action,
          user: activity.user,
          creation: activity.creation,
          data: activity.data || {},
        }
        activityMap.set(key, newGroup)
        grouped.push(newGroup)
      }
    } else {
      // For all other activities, add them as is without grouping
      grouped.push({
        doctype: 'GP Activity',
        name: activity.name,
        action: activity.action,
        user: activity.user,
        creation: activity.creation,
        data: activity.data || {},
      })
    }
  })

  return grouped.sort((a, b) => new Date(a.creation).getTime() - new Date(b.creation).getTime())
})

const timelineItems = computed(() => {
  let items: Array<GPComment | GroupedActivity> = []
  if (comments.data?.length) {
    items = items.concat(comments.data)
  }
  if (groupedActivities.value?.length) {
    items = items.concat(groupedActivities.value)
  }
  return items.sort((a, b) => new Date(a.creation) - new Date(b.creation))
})

const commentEmpty = computed(() => {
  return !draftData.value.content || draftData.value.content === '<p></p>'
})

const editorObject = computed(() => {
  return newCommentEditor.value?.editor
})

function openCommentBox() {
  showCommentBox.value = true
}

function openCommentBoxFromRow() {
  if (!showCommentBox.value) {
    openCommentBox()
  }
}

function resetCommentState() {
  showCommentBox.value = false
  highlightedItem.value = null
}

// ...existing methods converted to functions...
async function scrollToItem(item) {
  if (!item) return
  await nextTick()
  if (item.$el) {
    highlightedItem.value = item
    scrollToElement(item.$el)
  }
  setTimeout(() => {
    highlightedItem.value = null
    router.replace({ query: {} })
  }, 10000)
}

function scrollToElement($el: HTMLElement) {
  const scrollContainer = getScrollContainer()
  if (!scrollContainer) return
  const headerHeight = 64
  const top = $el.offsetTop - scrollContainer.scrollTop - headerHeight
  scrollContainer.scrollBy({ top, left: 0, behavior: 'smooth' })
}

function scrollToEnd() {
  const scrollContainer = getScrollContainer()
  if (!scrollContainer) return
  scrollContainer.scrollTop = scrollContainer.scrollHeight
}

// Add these functions after the existing methods
async function discardComment() {
  if (!editorObject.value?.isEmpty) {
    dialog.danger({
      title: 'Discard comment',
      message: 'Are you sure you want to discard your comment?',
      confirmLabel: 'Discard comment',
      onConfirm: async () => {
        await draft.clear()
        resetCommentState()
      },
    })
  } else {
    await draft.clear()
    resetCommentState()
  }
}

async function submitComment() {
  if (commentEmpty.value || comments.insert.loading) return

  const comment = await comments.insert.submit({
    reference_doctype: props.doctype,
    reference_name: props.name,
    content: draftData.value.content,
  })
  if (comments.insert.error || !comment?.name) return

  await draft.commit()
  resetCommentState()
}

function onNewCommentChange(content: string) {
  draftData.value.content = content
}

function setItemRef($component: any, item: any) {
  if ($component?.$el) {
    item.$el = $component.$el
  }
}

watch(showCommentBox, (val) => {
  if (val) {
    nextTick(() => {
      newCommentEditor.value?.editor.commands.focus()
      scrollToEnd()
    })
  }
})

// Reopen the composer if a saved draft is restored for this task.
watch(
  () => draft.ready.value,
  (ready) => {
    if (ready && draft.restored.value) showCommentBox.value = true
  },
  { immediate: true },
)

const unsubscribeFromDoc = subscribeToDoc(props.doctype, String(props.name))

socket.on('new_activity', (data: NewActivityEvent) => {
  // See CommentsArea.vue: the payload stringifies the id, but an integer-autonamed
  // doctype passes a number here, so a strict compare never matches.
  if (data.reference_doctype === props.doctype && data.reference_name === String(props.name)) {
    activities.reload()
  }
})

onUnmounted(() => {
  socket.off('new_activity')
  unsubscribeFromDoc()
})
</script>
