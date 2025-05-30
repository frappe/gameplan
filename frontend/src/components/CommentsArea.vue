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
    <div :style="{ paddingBottom: `${addCommentHeight + 80}px` }">
      <template v-for="(item, i) in timelineItems" :key="item.doctype + item.name">
        <div
          v-if="newMessagesFrom && newMessagesFrom == item.name"
          class="relative mb-4 mt-15"
          role="separator"
        >
          <div class="border-b border-blue-600"></div>
          <span
            class="absolute -top-2 left-1/2 -translate-x-1/2 bg-surface-white px-2 text-sm font-medium text-ink-blue-4"
          >
            New comments
          </span>
        </div>
        <Comment
          v-if="item.doctype == 'GP Comment'"
          :ref="($comment) => setItemRef($comment, item)"
          :comment="item"
          :highlight="
            highlightedItem?.doctype == item.doctype && highlightedItem?.name == item.name
          "
          :readOnlyMode="readOnlyMode"
          :comments="comments"
          @rich-quote="
            $emit('rich-quote', $event, { id: `comment:${item.name}`, author: item.owner })
          "
          @rich-quote-click="$emit('rich-quote-click', $event)"
        />
        <Activity
          :class="[
            {
              'pt-3': timelineItems[i - 1]?.doctype == 'GP Activity',
              'pt-15': timelineItems[i - 1]?.doctype != 'GP Activity',
            },
          ]"
          v-else-if="item.doctype == 'GP Activity'"
          :activity="item"
        />
        <Poll
          v-else-if="item.doctype == 'GP Poll'"
          :ref="($poll) => setItemRef($poll, item)"
          :highlight="
            highlightedItem?.doctype == item.doctype && highlightedItem?.name == item.name
          "
          :poll="item"
          :readOnlyMode="readOnlyMode"
        />
      </template>
    </div>

    <div
      v-if="!readOnlyMode && !disableNewComment"
      class="fixed z-[2] bottom-12 left-0 sm:left-auto px-4 sm:px-0 mb-px mt-2 w-full sm:max-w-3xl bg-surface-white py-3 sm:bottom-[-1px] standalone:bottom-16"
      ref="addComment"
    >
      <button
        class="flex w-full items-center rounded-lg bg-surface-gray-2 px-2 py-2 text-left text-base text-ink-gray-5 hover:bg-surface-gray-3"
        @click="showCommentBox = true"
        v-show="!showCommentBox"
      >
        <UserAvatar class="mr-3" :user="$user().name" size="sm" />
        Add a comment
      </button>
      <div
        v-show="showCommentBox"
        class="w-full rounded-lg border bg-surface-white p-4 focus-within:border-outline-gray-3"
        @keydown.ctrl.enter.capture.stop="submitComment"
        @keydown.meta.enter.capture.stop="submitComment"
      >
        <div class="mb-4 flex items-center">
          <UserAvatar :user="$user().name" size="md" />
          <span class="ml-2 text-base font-medium text-ink-gray-8">
            {{ $user().full_name }}
          </span>
          <TabButtons
            class="ml-auto"
            :buttons="[{ label: 'Comment' }, { label: 'Poll' }]"
            v-model="newCommentType"
          />
        </div>
        <CommentEditor
          ref="newCommentEditor"
          v-if="showCommentBox && newCommentType == 'Comment'"
          :key="commentEditorKey"
          :value="newComment"
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
          :editable="true"
          placeholder="Add a comment..."
        />
        <PollEditor
          v-show="newCommentType == 'Poll'"
          v-model:poll="newPoll"
          :submitButtonProps="{
            onClick: submitPoll,
            loading: polls.insert.loading,
          }"
          :discardButtonProps="{
            onClick: discardPoll,
          }"
        />
        <ErrorMessage :message="polls.insert.error" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted, watch, useTemplateRef } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useList } from 'frappe-ui/src/data-fetching'
import { TabButtons, ErrorMessage } from 'frappe-ui'
import CommentEditor from '@/components/CommentEditor.vue'
import Comment from './Comment.vue'
import Activity from './Activity.vue'
import PollEditor from './PollEditor.vue'
import Poll from './Poll.vue'
import UserAvatar from './UserAvatar.vue'
import { getScrollContainer } from '@/utils/scrollContainer'
import { createDialog } from '@/utils/dialogs'
import { useSocket } from '@/socket'
import { GPActivity, GPComment, GPPoll } from '@/types/doctypes'
import type { Editor } from '@tiptap/vue-3'
import { tags } from '@/data/tags'

interface Props {
  doctype: string
  name: string
  newCommentsFrom?: string
  readOnlyMode?: boolean
  disableNewComment?: boolean
}

interface NewPoll {
  title: string
  multiple_answers: boolean
  options: Array<{
    title: string
    idx: number
  }>
}

const props = withDefaults(defineProps<Props>(), {
  readOnlyMode: false,
  disableNewComment: false,
})

defineEmits<{
  (e: 'rich-quote', quote: string, author: string): void
  (e: 'rich-quote-click', payload: object): void
}>()

const router = useRouter()
const route = useRoute()
const socket = useSocket()

const showCommentBox = ref(false)
const newCommentType = ref<'Comment' | 'Poll'>('Comment')
const newComment = ref(localStorage.getItem(draftCommentKey()) || '')
const newPoll = ref({
  title: '',
  multiple_answers: false,
  anonymous: false,
  options: [
    { title: '', idx: 1 },
    { title: '', idx: 2 },
  ],
})
const newMessagesFrom = ref(props.newCommentsFrom)
const highlightedItem = ref<{ doctype: string; name: string } | null>(null)
const addCommentHeight = ref(0)
const newCommentEditor = useTemplateRef('newCommentEditor')
const addComment = ref(null)
let mutationObserver: MutationObserver | undefined
const commentEditorKey = ref(0)

const comments = useList<GPComment>({
  doctype: 'GP Comment',
  cacheKey: ['Comments', props.doctype, props.name],
  fields: [
    'name',
    'content',
    'owner',
    'creation',
    'modified',
    'deleted_at',
    { reactions: ['name', 'user', 'emoji'] },
  ],
  transform(data) {
    return data.map((d) => ({ ...d, doctype: 'GP Comment' }))
  },
  filters: {
    reference_doctype: props.doctype,
    reference_name: props.name,
  },
  orderBy: 'creation asc',
  limit: 99999,
  onSuccess() {
    if (route.query.comment) {
      if (route.query.comment === 'first_post') {
        router.replace({ query: {} })
        return
      }
      const comment = comments.data?.find((c) => c.name === route.query.comment)
      scrollToItem(comment)
    } else if (!route.query.fromSearch && comments.data?.length > 0) {
      scrollToEnd()
    }
  },
})

const activities = useList<GPActivity>({
  doctype: 'GP Activity',
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

const polls = useList<GPPoll>({
  doctype: 'GP Poll',
  fields: [
    'name',
    'title',
    'anonymous',
    'multiple_answers',
    'creation',
    'owner',
    'stopped_at',
    { options: ['name', 'title', 'idx', 'percentage'] },
    { votes: ['user', 'option'] },
    { reactions: ['name', 'user', 'emoji'] },
  ],
  filters: {
    discussion: props.name,
  },
  orderBy: 'creation asc',
  limit: 99999,
  transform(data) {
    return data.map((d) => ({ ...d, doctype: 'GP Poll' }))
  },
  onSuccess() {
    if (route.query.poll) {
      const poll = polls.data?.find((p) => p.name === route.query.poll)
      scrollToItem(poll)
    }
  },
})

// Computed
const timelineItems = computed(() => {
  let items: Array<GPComment | GPActivity | GPPoll> = []
  if (comments.data?.length) {
    items = items.concat(comments.data)
  }
  if (activities.data?.length) {
    items = items.concat(activities.data)
  }
  if (polls.data?.length) {
    items = items.concat(polls.data)
  }
  return items.sort((a, b) => new Date(a.creation).valueOf() - new Date(b.creation).valueOf())
})

const commentEmpty = computed(() => {
  return !newComment.value || newComment.value === '<p></p>'
})

const editorObject = computed<Editor | null>(() => {
  return newCommentEditor.value?.editor || null
})

defineExpose({
  editorObject,
  openCommentBox,
  scrollToCommentById,
  getCommentContentElement,
  highlightComment,
})

function draftCommentKey(): string {
  return `draft-comment-${props.doctype}-${props.name}`
}

function openCommentBox() {
  showCommentBox.value = true
  newCommentType.value = 'Comment'
}

function getCommentContentElement(id) {
  const comment = timelineItems.value?.find((c) => c.name === id)
  if (comment?.$el) {
    return comment.$el
  }
}

function highlightComment(id: string) {
  const comment = timelineItems.value?.find((c) => c.doctype == 'GP Comment' && c.name === id)
  if (comment) {
    highlightedItem.value = {
      doctype: comment.doctype,
      name: comment.name,
    }
    setTimeout(() => {
      highlightedItem.value = null
    }, 10000)
  }
}

function resetCommentState() {
  localStorage.removeItem(draftCommentKey())
  newComment.value = ''
  showCommentBox.value = false
  commentEditorKey.value++
  newCommentType.value = 'Comment'
  newPoll.value = {
    title: '',
    multiple_answers: false,
    anonymous: false,
    options: [
      { title: '', idx: 1 },
      { title: '', idx: 2 },
    ],
  }
  highlightedItem.value = null
}

async function submitComment() {
  if (commentEmpty.value) return

  comments.insert
    .submit({
      reference_doctype: props.doctype,
      reference_name: props.name,
      content: newComment.value,
    })
    .then(() => {
      resetCommentState()
      tags.reload()
    })
}

async function scrollToEnd() {
  await wait(50)
  _scrollToEnd()
  await wait(100)
  const scrollContainer = getScrollContainer()
  if (scrollContainer.scrollTop < scrollContainer.scrollHeight) {
    _scrollToEnd()
  }
}

function _scrollToEnd() {
  const scrollContainer = getScrollContainer()
  scrollContainer.scrollTop = scrollContainer.scrollHeight
}

function scrollToCommentById(id: string) {
  const item = timelineItems.value.find((item) => item.name === id)
  if (item) {
    scrollToItem(item)
  }
}

async function scrollToItem(item: any) {
  if (!item) return
  await nextTick()
  if (item.$el) {
    scrollToElement(item.$el)
    highlightedItem.value = {
      doctype: item.doctype,
      name: item.name,
    }
  }
  setTimeout(() => {
    highlightedItem.value = null
    router.replace({ query: {} })
  }, 10000)
}

async function scrollToElement($el: HTMLElement) {
  await wait(50)
  let top = _scrollToElement($el)
  await wait(100)
  const scrollContainer = getScrollContainer()
  if (scrollContainer.scrollTop != top) {
    _scrollToElement($el)
  }
}

function _scrollToElement($el: HTMLElement) {
  const scrollContainer = getScrollContainer()
  const headerHeight = 64
  const top = $el.offsetTop - scrollContainer.scrollTop - headerHeight
  scrollContainer.scrollBy({ top, left: 0 })
  return top
}

function wait(ms: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

function submitPoll() {
  if (props.doctype !== 'GP Discussion') return
  return polls.insert
    .submit({
      discussion: props.name,
      title: newPoll.value.title,
      anonymous: newPoll.value.anonymous ? 1 : 0,
      multiple_answers: newPoll.value.multiple_answers ? 1 : 0,
      options: newPoll.value.options,
    })
    .then(() => {
      resetCommentState()
    })
}

function discardPoll() {
  resetCommentState()
}

function setItemRef($component: any, item: any) {
  if ($component?.$el) {
    item.$el = $component.$el
  }
}

function onNewCommentChange(content: string) {
  newComment.value = content
  setTimeout(() => {
    localStorage.setItem(draftCommentKey(), content)
  }, 0)
}

function discardComment() {
  if (!editorObject.value?.isEmpty) {
    createDialog({
      title: 'Discard comment',
      message: 'Are you sure you want to discard your comment?',
      actions: [
        {
          label: 'Keep comment',
        },
        {
          label: 'Discard comment',
          onClick: ({ close }) => {
            resetCommentState()
            close()
          },
          variant: 'solid',
        },
      ],
    })
  } else {
    resetCommentState()
  }
}

watch(showCommentBox, (val) => {
  if (val) {
    nextTick(() => {
      editorObject.value?.commands.focus()
      scrollToEnd()
    })
  }
})

onMounted(() => {
  if (!commentEmpty.value) {
    showCommentBox.value = true
  }
  socket.on('new_activity', (data) => {
    if (data.reference_doctype === props.doctype && data.reference_name === props.name) {
      activities.reload()
    }
  })
  setupMutationObserver()
})

onUnmounted(() => {
  socket.off('new_activity')
  mutationObserver?.disconnect()
})

function setupMutationObserver() {
  const $el = addComment.value
  if (!$el) return

  const observer = new MutationObserver(() => {
    addCommentHeight.value = $el.clientHeight
  })
  observer.observe($el, { childList: true, subtree: true })
  mutationObserver = observer
}
</script>
