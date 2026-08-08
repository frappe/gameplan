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
    <div class="comments-timeline" :style="{ paddingBottom: `${addCommentHeight + 80}px` }">
      <template v-for="(item, i) in timelineItems" :key="item.doctype + item.name">
        <div
          v-if="newMessagesFrom && newMessagesFrom == item.name"
          class="relative mb-4 mt-15"
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
            'pt-14 sm:pt-0': needsMobileCommentGap(timelineItems, i, {
              includeFirstComment: true,
            }),
          }"
          :ref="($comment) => setItemRef($comment, item)"
          :comment="item"
          :space="space"
          :highlight="
            highlightedItem?.doctype == item.doctype && highlightedItem?.name == item.name
          "
          :readOnlyMode="readOnlyMode"
          :comments="comments"
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
          :space="space"
          :readOnlyMode="readOnlyMode"
        />
      </template>
    </div>

    <div
      v-if="!readOnlyMode && !disableNewComment && !hideNewComment"
      class="pointer-events-none fixed left-0 right-0 z-[2] w-full print:hidden sm:left-[274px] sm:right-1 sm:w-auto"
      :class="[
        isComposerFullscreen
          ? 'bottom-0 top-[var(--mobile-header-height)] z-20'
          : showCommentBox && !composerMinimized
            ? 'bottom-0 mt-2'
            : 'bottom-14 mt-2 sm:bottom-0 standalone:bottom-[4.5rem] standalone:sm:bottom-0',
        !showCommentBox || composerMinimized
          ? 'border-t border-outline-gray-2 bg-surface-base sm:border-t-0 sm:bg-transparent'
          : '',
      ]"
      ref="addComment"
    >
      <div class="pointer-events-auto" :class="{ 'h-full': isComposerFullscreen }">
        <div
          class="discussion-container bg-surface-base sm:bg-transparent"
          :class="isComposerFullscreen ? 'h-full py-0' : 'py-3'"
        >
          <div v-if="!showCommentBox" class="sm:-mx-3">
            <button
              type="button"
              class="flex w-full items-center gap-3 text-left sm:gap-0 sm:rounded-lg sm:bg-surface-elevation-2 sm:px-2 sm:py-2 sm:text-base sm:text-ink-gray-5 sm:hover:bg-surface-elevation-3 sm:shadow-md"
              @click="openCommentBox"
            >
              <UserAvatar class="sm:hidden" :user="$user().name" size="xl" />
              <UserAvatar class="mr-3 hidden sm:inline-block" :user="$user().name" size="sm" />
              <span
                class="flex h-8 min-w-0 flex-1 items-center rounded-md bg-surface-gray-2 px-3 text-md text-ink-gray-5 sm:hidden"
              >
                Add a comment
              </span>
              <span class="hidden sm:inline">Add a comment</span>
            </button>
          </div>
          <div
            v-else-if="composerMinimized"
            class="flex cursor-pointer items-center gap-3 text-left focus:outline-none sm:-mx-3 sm:gap-0 sm:rounded-lg sm:bg-surface-elevation-2 sm:py-1 sm:pl-2 sm:pr-1 sm:text-base sm:text-ink-gray-5 sm:shadow-md sm:hover:bg-surface-elevation-3 sm:focus:bg-surface-elevation-3"
            role="button"
            tabindex="0"
            @click="restoreComposer"
            @keydown.enter.prevent="restoreComposer"
            @keydown.space.prevent="restoreComposer"
          >
            <UserAvatar class="sm:hidden" :user="$user().name" size="xl" />
            <UserAvatar class="mr-3 hidden sm:inline-block" :user="$user().name" size="sm" />
            <span
              class="flex h-8 min-w-0 flex-1 items-center truncate rounded-md bg-surface-gray-2 px-3 text-md text-ink-gray-5 sm:h-auto sm:bg-transparent sm:px-0 sm:text-base sm:text-ink-gray-6"
            >
              {{ minimizedLabel }}
            </span>
            <Tooltip text="Expand">
              <Button
                class="shrink-0"
                variant="ghost"
                icon="lucide-maximize-2"
                label="Expand comment box"
                @click.stop="expandComposer"
              />
            </Tooltip>
          </div>
          <div
            v-else
            class="group/comment-composer relative -mx-3 bg-surface-base p-4 sm:bg-surface-elevation-2 sm:p-3 sm:shadow-md"
            :class="
              isComposerFullscreen
                ? 'flex h-full flex-col'
                : 'border-t border-outline-gray-2 sm:rounded-lg sm:border-t-0'
            "
            :aria-busy="isDraftLoading"
            :inert="isDraftLoading"
            @keydown.ctrl.enter.capture.stop="submitComment"
            @keydown.meta.enter.capture.stop="submitComment"
          >
            <div v-if="isDraftLoading" role="status" class="mb-2 text-sm text-ink-gray-5">
              Loading draft…
            </div>
            <button
              type="button"
              class="absolute left-1/2 top-0 z-10 hidden h-6 w-24 -translate-x-1/2 cursor-ns-resize touch-none items-center justify-center rounded-full opacity-60 transition-opacity hover:opacity-100 focus:opacity-100 group-hover/comment-composer:opacity-100 sm:flex"
              aria-label="Resize comment box"
              @pointerdown.stop="startComposerResize"
            >
              <span class="h-1 w-10 rounded-full bg-surface-gray-4" />
            </button>
            <div class="mb-3 flex items-center gap-2">
              <UserAvatar class="sm:hidden" :user="$user().name" size="lg" />
              <UserAvatar class="hidden sm:inline-block" :user="$user().name" size="md" />
              <span
                class="min-w-0 flex-1 truncate text-lg-medium text-ink-gray-8 sm:text-base-medium"
              >
                {{ $user().full_name }}
              </span>
              <div class="hidden sm:block">
                <TabButtons
                  :buttons="[{ label: 'Comment' }, { label: 'Poll' }]"
                  v-model="newCommentType"
                />
              </div>
              <Tooltip :text="isComposerFullscreen ? 'Minimize' : 'Expand'">
                <Button
                  class="sm:hidden"
                  variant="ghost"
                  :icon="isComposerFullscreen ? 'lucide-minimize-2' : 'lucide-maximize-2'"
                  :label="isComposerFullscreen ? 'Minimize comment box' : 'Expand comment box'"
                  @click="toggleMobileComposerFullscreen"
                />
              </Tooltip>
              <Tooltip text="Minimize">
                <Button
                  class="hidden sm:inline-flex"
                  variant="ghost"
                  icon="lucide-minimize-2"
                  label="Minimize comment box"
                  @click="minimizeComposer"
                />
              </Tooltip>
            </div>
            <CommentEditor
              ref="newCommentEditor"
              v-if="newCommentType == 'Comment'"
              :key="commentEditorKey"
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
              :editable="!isDraftLoading"
              :max-height="activeComposerEditorMaxHeightStyle"
              :min-height="activeComposerEditorMinHeightStyle"
              v-model:toolbar-expanded="composerToolbarExpanded"
              placeholder="Add a comment..."
            >
              <template #actions-left>
                <TabButtons
                  :buttons="[{ label: 'Comment' }, { label: 'Poll' }]"
                  v-model="newCommentType"
                />
              </template>
            </CommentEditor>
            <ErrorMessage :message="comments.insert.error" />
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
            >
              <template #actions-left>
                <TabButtons
                  :buttons="[{ label: 'Comment' }, { label: 'Poll' }]"
                  v-model="newCommentType"
                />
              </template>
            </PollEditor>
            <ErrorMessage :message="polls.insert.error" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  ref,
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  watch,
  watchEffect,
  useTemplateRef,
} from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useEventListener } from '@vueuse/core'
import { useList, TabButtons, ErrorMessage, Button, Tooltip } from 'frappe-ui'
import CommentEditor from '@/components/editor/CommentEditor.vue'
import Comment from './Comment.vue'
import Activity from './Activity.vue'
import PollEditor from './PollEditor.vue'
import Poll from './Poll.vue'
import UserAvatar from './UserAvatar.vue'
import { getScrollContainer } from 'frappe-ui'
import { dialog } from 'frappe-ui'
import { subscribeToDoc, useSocket, type NewActivityEvent } from '@/socket'
import { GPActivity, GPComment, GPPoll } from '@/types/doctypes'
import type { Editor } from '@tiptap/vue-3'
import { tags } from '@/data/tags'
import { isNewCommentOpen } from '@/data/newComment'
import { useRichQuotes } from '@/components/RichQuoteExtension/useRichQuotes'
import { useDraftSync } from '@/data/useDraftSync'
import { onReconnect } from '@/data/online'
import { useSessionUser } from '@/data/users'
import type { Space } from '@/data/spaces'
import { useIsMobile } from 'frappe-ui'
import { needsMobileCommentGap } from '@/utils/commentTimeline'

interface Props {
  doctype: string
  name: string
  // The space this thread lives in, used to derive community-admin moderation
  // rights for deleting others' comments/polls.
  space?: Space | null
  newCommentsFrom?: string
  readOnlyMode?: boolean
  disableNewComment?: boolean
  // transient: hide the fixed comment bar while the post itself is being edited
  hideNewComment?: boolean
  // Bumped by the parent whenever this client's own action changes the reference
  // document (pass its `modified`). Lets the timeline refresh for the acting user
  // without waiting on the `new_activity` socket echo — see the watch below.
  activityVersion?: string | number
}

interface NewPoll {
  title: string
  anonymous: boolean
  multiple_answers: boolean
  options: Array<{
    title: string
    idx: number
  }>
}

interface ComposerUiState {
  open?: boolean
  minimized?: boolean
  toolbarExpanded?: boolean
  editorMaxHeight?: number
  editorMinHeight?: number | null
  type?: 'Comment' | 'Poll'
  poll?: NewPoll
}

const DEFAULT_COMPOSER_EDITOR_HEIGHT = 560
// Floor for the open composer: it never renders (or restores) shorter than this.
const MIN_COMPOSER_EDITOR_HEIGHT = 100
// Drag the resize handle so the editor shrinks past this height and the composer collapses
// instead of shrinking further. Deliberately 0: the composer only gives way to the
// collapsed bar once it has shrunk all the way down, which tested as the more natural
// hand-off than collapsing early. (Intentional — not the unreachable-threshold bug it looks like.)
const MINIMIZE_COMPOSER_THRESHOLD = 0
const MAX_COMPOSER_EDITOR_VIEWPORT_RATIO = 0.72

const props = withDefaults(defineProps<Props>(), {
  readOnlyMode: false,
  disableNewComment: false,
  hideNewComment: false,
})

const router = useRouter()
const route = useRoute()
const socket = useSocket()
let unsubscribeFromDoc: (() => void) | null = null
const sessionUser = useSessionUser()
const isMobileViewport = useIsMobile()

const showCommentBox = ref(false)
const composerMinimized = ref(false)
const mobileComposerFullscreen = ref(false)
const composerToolbarExpanded = ref(false)
const composerEditorMaxHeight = ref(DEFAULT_COMPOSER_EDITOR_HEIGHT)
const composerEditorMinHeight = ref<number | null>(null)
const composerStateLoaded = ref(false)
const newCommentType = ref<'Comment' | 'Poll'>('Comment')

// The new-comment composer is an auto-saved draft, keyed to this discussion so it
// survives reloads and restores across tabs. One draft per (user, discussion).
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
const isDraftLoading = draft.isLoading
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
const addComment = useTemplateRef('addComment')
let mutationObserver: MutationObserver | undefined
let resizeObserver: ResizeObserver | undefined
const commentEditorKey = ref(0)

const richQuotes = useRichQuotes()

const composerStorageKey = computed(() => {
  return ['gameplan', 'comment-composer', sessionUser.name, props.doctype, props.name].join(':')
})

const comments = useList<GPComment>({
  doctype: 'GP Comment',
  // Scoped to the session user: a discussion's comments can live in a private space,
  // so a second account on the same browser must not see them cached offline before
  // its own permission-checked fetch resolves (review finding from PR #516).
  cacheKey: ['Comments', props.doctype, props.name, sessionUser.name],
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
  cacheKey: ['Activities', props.doctype, props.name, sessionUser.name],
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

// The timeline normally updates live via the `new_activity` socket event (see
// onMounted). Independent of that server round trip, the user who just
// renamed/closed/moved the discussion should see their own action recorded at once.
// The parent bumps `activityVersion` with the doc's `modified` on every such action,
// so reload the timeline when it changes (skipping the initial undefined -> value
// transition on first load, when the list has already fetched on mount).
watch(
  () => props.activityVersion,
  (next, prev) => {
    if (prev !== undefined && next !== prev) activities.reload()
  },
)

const polls = useList<GPPoll>({
  doctype: 'GP Poll',
  cacheKey: ['Polls', props.name, sessionUser.name],
  staleOnError: true,
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

watchEffect(() => {
  if (richQuotes) {
    richQuotes.commentsData.value = comments.data ?? null
  }
})

// US5 (seamless recovery): while offline, comments/activity/polls posted by
// other users never arrive — the socket that normally pushes them is down too.
// Reload this discussion's timeline once the browser comes back online.
// Unregistered on unmount: this callback closes over lists owned by this
// component instance, and there's no reason to keep refetching an open
// discussion the user has already navigated away from.
const unregisterReconnect = onReconnect(() => {
  comments.reload()
  activities.reload()
  polls.reload()
})
onUnmounted(unregisterReconnect)

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
  return !draftData.value.content || draftData.value.content === '<p></p>'
})

const editorObject = computed<Editor | null>(() => {
  return newCommentEditor.value?.editor || null
})

const minimizedLabel = computed(() => {
  if (newCommentType.value === 'Poll') return newPoll.value.title || 'Poll in progress'
  return draftContentPreview.value || 'Add a comment'
})

const draftContentPreview = computed(() => {
  const text = firstTextBlock(draftData.value.content ?? '')
  return text ? `${text}...` : ''
})

const composerEditorMaxHeightStyle = computed(() => `${composerEditorMaxHeight.value}px`)
// Before an explicit resize (min unset) the composer still keeps a floor so it
// never opens shorter than the resize minimum — that's what makes drag-resizing
// start from a stable height instead of snapping up from a content-sized box.
const composerEditorMinHeightStyle = computed(
  () => `${composerEditorMinHeight.value ?? MIN_COMPOSER_EDITOR_HEIGHT}px`,
)
const mobileComposerEditorHeightStyle = 'calc(100dvh - var(--mobile-header-height) - 10.5rem)'
const mobileComposerEditorShortHeightStyle = '12rem'
const isComposerFullscreen = computed(
  () =>
    isMobileViewport.value &&
    showCommentBox.value &&
    !composerMinimized.value &&
    mobileComposerFullscreen.value,
)
const activeComposerEditorMaxHeightStyle = computed(() =>
  isMobileViewport.value
    ? mobileComposerFullscreen.value
      ? mobileComposerEditorHeightStyle
      : mobileComposerEditorShortHeightStyle
    : composerEditorMaxHeightStyle.value,
)
const activeComposerEditorMinHeightStyle = computed(() =>
  isMobileViewport.value
    ? mobileComposerFullscreen.value
      ? mobileComposerEditorHeightStyle
      : undefined
    : composerEditorMinHeightStyle.value,
)

defineExpose({
  editorObject,
  openCommentBox,
  scrollToCommentById,
  getCommentContentElement,
  highlightComment,
})

function openCommentBox() {
  showCommentBox.value = true
  composerMinimized.value = false
  mobileComposerFullscreen.value = false
  newCommentType.value = 'Comment'
}

function minimizeComposer() {
  if (isMobileViewport.value && mobileComposerFullscreen.value) {
    mobileComposerFullscreen.value = false
    return
  }
  composerMinimized.value = true
  mobileComposerFullscreen.value = false
}

function restoreComposer() {
  // Ignore the synthetic click that fires when a resize-drag is released on the
  // collapsed bar — that same gesture just minimized it.
  if (Date.now() - dragMinimizedAt < 300) return
  composerMinimized.value = false
  mobileComposerFullscreen.value = false
  nextTick(() => {
    editorObject.value?.commands.focus()
  })
}

function expandMobileComposer() {
  showCommentBox.value = true
  composerMinimized.value = false
  mobileComposerFullscreen.value = true
  nextTick(() => {
    editorObject.value?.commands.focus()
  })
}

function expandComposer() {
  if (isMobileViewport.value) {
    expandMobileComposer()
  } else {
    restoreComposer()
  }
}

function toggleMobileComposerFullscreen() {
  if (mobileComposerFullscreen.value) {
    minimizeComposer()
  } else {
    expandMobileComposer()
  }
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
  showCommentBox.value = false
  composerMinimized.value = false
  mobileComposerFullscreen.value = false
  composerToolbarExpanded.value = false
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
  isNewCommentOpen.value = false
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
  tags.reload()
}

async function scrollToEnd() {
  await wait(50)
  _scrollToEnd()
  await wait(100)
  const scrollContainer = getScrollContainer()
  if (!scrollContainer) return
  if (scrollContainer.scrollTop < scrollContainer.scrollHeight) {
    _scrollToEnd()
  }
}

function _scrollToEnd() {
  const scrollContainer = getScrollContainer()
  if (!scrollContainer) return
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
  if (!scrollContainer) return
  if (scrollContainer.scrollTop != top) {
    _scrollToElement($el)
  }
}

function _scrollToElement($el: HTMLElement) {
  const scrollContainer = getScrollContainer()
  if (!scrollContainer) return 0
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
  draftData.value.content = content
}

async function discardComment() {
  if (!editorObject.value?.isEmpty) {
    dialog.danger({
      title: 'Discard comment',
      message: 'Are you sure you want to discard your comment?',
      confirmLabel: 'Discard comment',
      cancelLabel: 'Keep comment',
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

watch(showCommentBox, (val) => {
  updateGlobalCommentState()
  if (val && !composerMinimized.value) {
    nextTick(() => {
      editorObject.value?.commands.focus()
      scrollToEnd()
    })
  }
})

watch(composerMinimized, (minimized) => {
  updateGlobalCommentState()
  if (!minimized && showCommentBox.value) {
    nextTick(() => {
      editorObject.value?.commands.focus()
    })
  }
})

watch(
  [
    showCommentBox,
    composerMinimized,
    composerToolbarExpanded,
    composerEditorMaxHeight,
    composerEditorMinHeight,
    newCommentType,
    newPoll,
  ],
  () => {
    saveComposerState()
  },
  { deep: true },
)

watch(
  composerStorageKey,
  () => {
    loadComposerState()
  },
  { immediate: true },
)

// Reopen the composer if a saved draft is restored for this discussion.
watch(
  () => draft.ready.value,
  (ready) => {
    if (ready && draft.restored.value) showCommentBox.value = true
  },
  { immediate: true },
)

// Opened from the Drafts list (?draft=comment): surface the restored reply by expanding
// and focusing the composer, then drop the flag so later edits don't re-trigger it.
watch(
  () => draft.ready.value,
  (ready) => {
    if (!ready || route.query.draft !== 'comment') return
    showCommentBox.value = true
    composerMinimized.value = false
    nextTick(() => {
      editorObject.value?.commands.focus('end')
      scrollToEnd()
    })
    const query = { ...route.query }
    delete query.draft
    router.replace({ query })
  },
  { immediate: true },
)

onMounted(() => {
  // Announce this area's reply box (quote insert target) and its comments (scroll
  // targets) to the rich-quote controller, instead of being reached into.
  richQuotes?.setReplyTarget({
    open: openCommentBox,
    getEditor: () => editorObject.value,
  })
  richQuotes?.setCommentNavigator({
    getCommentEl: getCommentContentElement,
    scrollToComment: scrollToCommentById,
    highlightComment,
  })
  unsubscribeFromDoc = subscribeToDoc(props.doctype, String(props.name))
  socket.on('new_activity', (data: NewActivityEvent) => {
    // The payload stringifies the id (activity.py) but doctypes that autoname to an
    // integer hand this component a number, so a strict compare never matches and the
    // timeline silently stops updating. Compare as strings.
    if (data.reference_doctype === props.doctype && data.reference_name === String(props.name)) {
      activities.reload()
    }
  })
  setupComposerMeasurement()
})

onUnmounted(() => {
  richQuotes?.setReplyTarget(null)
  richQuotes?.setCommentNavigator(null)
  socket.off('new_activity')
  unsubscribeFromDoc?.()
  mutationObserver?.disconnect()
  resizeObserver?.disconnect()
  stopComposerResize()
  isNewCommentOpen.value = false
})

function setupComposerMeasurement() {
  const $el = addComment.value
  if (!$el) return

  updateComposerHeight()

  mutationObserver = new MutationObserver(updateComposerHeight)
  mutationObserver.observe($el, { childList: true, subtree: true })

  resizeObserver = new ResizeObserver(updateComposerHeight)
  resizeObserver.observe($el)
}

function updateComposerHeight() {
  addCommentHeight.value = addComment.value?.clientHeight ?? 0
}

function updateGlobalCommentState() {
  isNewCommentOpen.value = showCommentBox.value && !composerMinimized.value
}

function loadComposerState() {
  composerStateLoaded.value = false
  const state = readComposerState()
  showCommentBox.value = Boolean(state.open)
  composerMinimized.value = Boolean(state.minimized)
  composerToolbarExpanded.value = Boolean(state.toolbarExpanded)
  composerEditorMaxHeight.value = normalizeComposerHeight(state.editorMaxHeight)
  composerEditorMinHeight.value =
    state.editorMinHeight == null ? null : normalizeComposerHeight(state.editorMinHeight)
  newCommentType.value = state.type ?? 'Comment'
  newPoll.value = normalizePoll(state.poll)
  composerStateLoaded.value = true
  updateGlobalCommentState()
}

function saveComposerState() {
  if (!composerStateLoaded.value) return
  localStorage.setItem(
    composerStorageKey.value,
    JSON.stringify({
      open: showCommentBox.value,
      minimized: composerMinimized.value,
      toolbarExpanded: composerToolbarExpanded.value,
      editorMaxHeight: composerEditorMaxHeight.value,
      editorMinHeight: composerEditorMinHeight.value,
      type: newCommentType.value,
      poll: newPoll.value,
    } satisfies ComposerUiState),
  )
}

function readComposerState(): ComposerUiState {
  try {
    return JSON.parse(localStorage.getItem(composerStorageKey.value) || '{}')
  } catch {
    return {}
  }
}

function normalizePoll(poll?: ComposerUiState['poll']): NewPoll {
  return {
    title: poll?.title ?? '',
    multiple_answers: Boolean(poll?.multiple_answers),
    anonymous: Boolean(poll?.anonymous),
    options: poll?.options?.length
      ? poll.options.map((option, index) => ({
          title: option.title ?? '',
          idx: option.idx || index + 1,
        }))
      : [
          { title: '', idx: 1 },
          { title: '', idx: 2 },
        ],
  }
}

function firstTextBlock(html: string) {
  const doc = new DOMParser().parseFromString(html, 'text/html')
  const blocks = Array.from(doc.body.querySelectorAll('p, li, blockquote, h1, h2, h3, h4, h5, h6'))
  const firstBlock = blocks.find((block) => block.textContent?.trim())
  return firstBlock?.textContent?.replace(/\s+/g, ' ').trim() ?? ''
}

let resizeStartY = 0
let resizeStartHeight = DEFAULT_COMPOSER_EDITOR_HEIGHT
let resizeHandle: HTMLElement | null = null
let resizePointerId: number | null = null
// Timestamp of a drag that ended in the minimized state — used to swallow the
// click the browser synthesizes on release so it doesn't instantly reopen.
let dragMinimizedAt = 0

function startComposerResize(event: PointerEvent) {
  event.preventDefault()
  // Capture on the stable composer container, not the handle button — the button
  // unmounts when the drag minimizes the composer, but the container stays put, so
  // capture (and thus an upward drag back to reopen) survives the collapse.
  resizeHandle = addComment.value ?? (event.currentTarget as HTMLElement)
  resizePointerId = event.pointerId
  resizeHandle.setPointerCapture?.(event.pointerId)
  resizeStartY = event.clientY
  // Seed from the editor's actual rendered height (not the stored max), so the
  // drag continues smoothly from where the box currently is instead of jumping
  // to the cap on the first pointer move.
  const editorEl = editorObject.value?.view?.dom as HTMLElement | undefined
  resizeStartHeight = editorEl?.getBoundingClientRect().height ?? composerEditorMaxHeight.value
  document.body.style.cursor = 'ns-resize'
  document.body.style.userSelect = 'none'
  window.addEventListener('pointermove', resizeComposer)
  window.addEventListener('pointerup', stopComposerResize)
  window.addEventListener('pointercancel', stopComposerResize)
}

function resizeComposer(event: PointerEvent) {
  const nextHeight = resizeStartHeight + resizeStartY - event.clientY
  // Below the threshold the composer collapses, but the drag stays live: keep
  // tracking so pulling back up past the threshold reopens and resizes it.
  if (nextHeight < MINIMIZE_COMPOSER_THRESHOLD) {
    composerMinimized.value = true
    // Heights shrank with the drag; reset them so a later restore (or a drag back
    // up) reopens at the normal size instead of the ~50px we collapsed through.
    composerEditorMinHeight.value = null
    composerEditorMaxHeight.value = DEFAULT_COMPOSER_EDITOR_HEIGHT
    return
  }
  composerMinimized.value = false
  const viewportMax = Math.floor(window.innerHeight * MAX_COMPOSER_EDITOR_VIEWPORT_RATIO)
  const height = Math.min(nextHeight, viewportMax)
  composerEditorMaxHeight.value = height
  composerEditorMinHeight.value = height
}

function stopComposerResize() {
  if (
    resizeHandle &&
    resizePointerId != null &&
    resizeHandle.hasPointerCapture?.(resizePointerId)
  ) {
    resizeHandle.releasePointerCapture(resizePointerId)
  }
  resizeHandle = null
  resizePointerId = null
  // Arm the click-swallow only when the drag actually left the composer collapsed.
  if (composerMinimized.value) dragMinimizedAt = Date.now()
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  window.removeEventListener('pointermove', resizeComposer)
  window.removeEventListener('pointerup', stopComposerResize)
  window.removeEventListener('pointercancel', stopComposerResize)
}

function normalizeComposerHeight(height?: number) {
  const viewportMaxHeight = Math.floor(window.innerHeight * MAX_COMPOSER_EDITOR_VIEWPORT_RATIO)
  const maxHeight = Math.max(MIN_COMPOSER_EDITOR_HEIGHT, viewportMaxHeight)
  return Math.min(
    Math.max(Math.round(height || DEFAULT_COMPOSER_EDITOR_HEIGHT), MIN_COMPOSER_EDITOR_HEIGHT),
    maxHeight,
  )
}

// Re-clamp a previously-sized composer when the window shrinks, so a tall box
// never spills past the (smaller) viewport. normalizeComposerHeight folds in the
// current viewport cap; the min is only touched when it was explicitly set
// (coupled by a resize) — grow mode leaves it null so the floor still applies.
function clampComposerToViewport() {
  composerEditorMaxHeight.value = normalizeComposerHeight(composerEditorMaxHeight.value)
  if (composerEditorMinHeight.value != null) {
    composerEditorMinHeight.value = normalizeComposerHeight(composerEditorMinHeight.value)
  }
}
useEventListener(window, 'resize', clampComposerToViewport)
</script>
