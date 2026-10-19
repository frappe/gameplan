<template>
  <div class="relative" :data-id="comment.name">
    <div
      v-if="highlight"
      class="absolute inset-0 translate-y- z-[5] rounded-4 border-2 -mx-4 -mb-4 mt-11 pointer-events-none"
    />
    <!--
      The author row is opaque, so while it is sticky it paints over the top of
      the comment's own body once the comment is taller than the scrollport —
      fine when reading, but it buries the line you are typing while editing
      (worst on a phone, where it eats ~56px of a keyboard-shrunk viewport).
      Same treatment the post editor already gets in DiscussionView.

      The negative margins widen the opaque row out to the container's padding
      edge. A selected image paints a ring 4px outside its own box, and that box
      is already the full column width, so a row that stopped at the column edge
      let the ring show above it. Same fix as DiscussionView.
    -->
    <div
      class="flex items-center bg-surface-base pb-2 pt-2 text-md text-ink-gray-8 sm:pt-14 sm:text-base"
      :class="{
        'sticky -top-px z-[1] -mx-3 px-3 sm:-mx-5 sm:px-5 sm:top-0': !isEditing,
      }"
    >
      <UserProfileLink class="mr-3" :user="author.name">
        <UserAvatarWithHover class="sm:hidden" size="xl" :user="author.name" />
        <UserAvatarWithHover class="hidden sm:inline-flex" size="lg" :user="author.name" />
      </UserProfileLink>
      <div class="md:flex md:items-center">
        <UserProfileLink
          class="text-md-medium hover:text-ink-gray-9 sm:text-base sm:font-medium"
          :user="author.name"
        >
          {{ author.full_name }}
          <span class="hidden md:inline">&nbsp;&middot;&nbsp;</span>
        </UserProfileLink>
        <div>
          <Tooltip :text="dayjsLocal(comment.creation).format('D MMM YYYY [at] h:mm A')">
            <time class="text-p-base text-ink-gray-5 sm:text-base" :datetime="comment.creation">
              {{ dayjsLocal(comment.creation).fromNow() }}
            </time>
          </Tooltip>
          <Tooltip
            v-if="comment.edited_at"
            :text="dayjsLocal(comment.edited_at).format('D MMM YYYY [at] h:mm A')"
          >
            <span class="text-ink-gray-5"> &nbsp;&middot; Edited </span>
          </Tooltip>
          <span v-if="isUpdating" class="italic text-ink-gray-5"> &nbsp;&middot; Sending... </span>
          <span
            v-if="updateError"
            class="inline-flex items-center whitespace-nowrap text-ink-red-7"
          >
            &nbsp;&middot;&nbsp;Not saved
          </span>
        </div>
      </div>
      <Dropdown
        v-if="!isEditing && !isUpdating"
        class="ml-auto print:hidden"
        align="end"
        :button="{
          icon: 'lucide-more-horizontal',
          variant: 'ghost',
          label: 'Comment Options',
          disabled: isUpdating,
        }"
        :options="dropdownOptions"
      />
    </div>
    <div class="flex-1" :aria-busy="isDraftLoading" :inert="isDraftLoading">
      <div v-if="isDraftLoading" role="status" class="mb-2 text-sm text-ink-gray-5">
        Loading draft…
      </div>
      <div
        :class="{
          'w-full rounded-6 border bg-surface-base p-4 focus-within:border-outline-gray-3':
            isEditing,
        }"
        @keydown.ctrl.enter.capture.stop="updateComment()"
        @keydown.meta.enter.capture.stop="updateComment()"
      >
        <div v-if="comment.hidden_at || comment.spam_removed_at" class="text-base text-ink-gray-5">
          <p>
            {{
              comment.spam_removed_at
                ? 'This reply was removed by a moderator.'
                : 'This reply was hidden by a moderator.'
            }}
          </p>
          <Button v-if="canModerate" class="mt-2" variant="ghost" @click="toggleHiddenContent">
            {{ hiddenContent ? 'Close preview' : 'View hidden reply' }}
          </Button>
          <CommentEditor v-if="hiddenContent" :value="hiddenContent" :editable="false" />
        </div>
        <CommentEditor
          v-else-if="comment.deleted_at == null"
          :quote-source-id="`comment:${comment.name}`"
          :author="comment.owner"
          :value="isEditing && draftData ? draftData.content : comment.content"
          @change="onEditorChange"
          :editable="isEditing && !isDraftLoading"
          :submitButtonProps="{
            onClick: () => updateComment(),
            loading: isUpdating,
          }"
          :discardButtonProps="{
            onClick: () => discardEdit(),
          }"
        />
        <span class="text-base italic text-ink-gray-5" v-else> This message is deleted </span>
        <ErrorMessage v-if="isEditing" class="mt-2" :message="updateErrorMessage" />
        <div
          class="mt-3"
          v-if="!comment.deleted_at && !comment.hidden_at && !comment.spam_removed_at && !isEditing"
        >
          <Reactions doctype="GP Comment" :name="comment.name" :read-only-mode="readOnlyMode" />
        </div>
      </div>
    </div>
    <RevisionsDialog
      v-model="showRevisionsDialog"
      doctype="GP Comment"
      :name="comment.name"
      fieldname="content"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, defineAsyncComponent, watch } from 'vue'
import { Button, Dropdown, ErrorMessage, Tooltip, dayjsLocal, useDoctype } from 'frappe-ui'
import { useList } from 'frappe-ui'
import { copyToClipboard, extractServerMessage } from '@/utils'
import UserProfileLink from './UserProfileLink.vue'
import CommentEditor from './editor/CommentEditor.vue'
import Reactions from './Reactions.vue'
// Lazy: htmldiff-js + motion-v only load when a viewer opens edit history.
const RevisionsDialog = defineAsyncComponent(() => import('./RevisionsDialog.vue'))
import UserAvatarWithHover from './UserAvatarWithHover.vue'
import { GPBookmark, GPComment } from '@/types/doctypes'
import { dialog } from 'frappe-ui'
import { tags } from '@/data/tags'
import { useDraftSync } from '@/data/useDraftSync'
import { useUser, useSessionUser } from '@/data/users'
import type { Space } from '@/data/spaces'
import { canDeleteContent, canEditContent, canModerateSpace } from '@/utils/permissions'
import { postedPollInContent } from '@/components/PollBlock/poll-draft'
import { captureError } from '@/utils/errorReporting'
import { isAnonymousVisitor } from '@/utils/publicAccess'

interface Props {
  comment: GPComment
  readOnlyMode?: boolean
  highlight?: boolean
  comments: ReturnType<typeof useList<GPComment>>
  bookmarks?: ReturnType<typeof useList<GPBookmark>>
  // Space the comment's thread belongs to, for community-admin delete moderation.
  space?: Space | null
}

const props = defineProps<Props>()
const showRevisionsDialog = ref(false)
const commentType = useDoctype<GPComment>('GP Comment')
const hiddenContent = ref('')
const canModerate = computed(
  () =>
    props.comment.reference_doctype === 'GP Discussion' &&
    canModerateSpace(props.space, useSessionUser()),
)
watch(
  () => [props.comment.hidden_at, props.comment.spam_removed_at],
  () => {
    hiddenContent.value = ''
  },
)

async function toggleHiddenContent() {
  updateError.value = null
  try {
    hiddenContent.value = hiddenContent.value
      ? ''
      : await commentType.runDocMethod.submit({
          name: props.comment.name,
          method: 'get_hidden_content',
        })
  } catch (error) {
    updateError.value = error
  }
}

function moderateReply(spam = false) {
  const restore = !spam && Boolean(props.comment.hidden_at || props.comment.spam_removed_at)
  dialog.prompt({
    title: restore ? 'Restore reply' : spam ? 'Delete spam' : 'Hide reply',
    message: restore
      ? 'Make this reply visible again?'
      : 'The reply will show a placeholder. Existing quotations in other posts stay unchanged.',
    fields: restore ? [] : [{ name: 'reason', label: 'Reason', type: 'textarea', required: true }],
    confirmLabel: restore ? 'Restore reply' : spam ? 'Delete spam' : 'Hide reply',
    onConfirm: async ({ values }) => {
      await commentType.runDocMethod.submit({
        name: props.comment.name,
        method: restore ? 'restore' : spam ? 'delete_spam' : 'hide',
        params: restore ? {} : { reason: values.reason },
      })
      hiddenContent.value = ''
      await props.comments.reload()
    },
  })
}
const isEditing = ref(false)
const isUpdating = ref(false)
const updateError = ref(null)
// Why the server refused the edit, e.g. a new account's 24-hour edit window.
const updateErrorMessage = computed(
  () => extractServerMessage(updateError.value) || 'Could not save',
)
const author = computed(() => useUser(props.comment.owner))

// While editing, the comment body is an auto-saved draft: it survives reloads and
// silently restores if the edit is reopened. Dormant until the editor is open.
const draft = useDraftSync({
  identity: () => ({
    type: 'Comment',
    mode: 'Edit',
    referenceDoctype: 'GP Comment',
    referenceName: props.comment.name,
  }),
  enabled: isEditing,
  initialPayload: () => ({ content: props.comment.content ?? '' }),
})
const draftData = draft.data
const isDraftLoading = draft.isLoading

const onEditorChange = (value: string) => {
  // Ignored unless this editor is in edit mode with a resolved draft behind it — while it
  // displays the saved comment, or while the draft is still loading, it owns no buffer.
  if (!isEditing.value || !draftData.value) return
  draftData.value.content = value
}

const startEditing = () => {
  isEditing.value = true
}

const discardEdit = async () => {
  isEditing.value = false
  updateError.value = null
  await draft.clear()
}

const updateComment = () => {
  const content = draftData.value?.content
  if (!content?.trim()) return

  // Saving without the poll block deletes the poll and its votes, and a stray
  // Backspace is enough to remove the block, so ask first.
  const poll = postedPollInContent(props.comment.content)
  if (poll && postedPollInContent(content) !== poll) {
    dialog.danger({
      title: 'Remove poll',
      message: 'Saving this comment deletes its poll and all its votes. This cannot be undone.',
      confirmLabel: 'Remove poll',
      onConfirm: () => saveComment(content),
    })
    return
  }
  return saveComment(content)
}

const saveComment = async (content: string) => {
  isUpdating.value = true
  updateError.value = null

  try {
    await props.comments.setValue.submit({
      name: props.comment.name,
      content,
    })
    await draft.commit()
    isEditing.value = false
    tags.reload()
  } catch (error) {
    updateError.value = error
  } finally {
    isUpdating.value = false
  }
}

const commentDoctype = useDoctype<GPComment>('GP Comment')

const isBookmarked = computed(() =>
  Boolean(props.bookmarks?.data?.some((b) => String(b.comment) === String(props.comment.name))),
)

const runBookmark = (method: 'add_bookmark' | 'remove_bookmark') =>
  commentDoctype.runDocMethod
    .submit({ name: props.comment.name, method })
    .then(() => props.bookmarks?.reload())
    .catch((error) =>
      captureError(error, { action: method.replace('_', '-'), comment: props.comment.name }),
    )

const copyLink = (comment: GPComment) => {
  const location = window.location
  const url = `${location.origin}${location.pathname}?comment=${comment.name}`
  copyToClipboard(url)
}

const dropdownOptions = computed(() => [
  {
    label:
      props.comment.hidden_at || props.comment.spam_removed_at ? 'Restore reply' : 'Hide reply',
    icon: props.comment.hidden_at ? 'lucide-eye' : 'lucide-eye-off',
    onClick: () => moderateReply(),
    condition: () => canModerate.value && !props.comment.deleted_at && !props.readOnlyMode,
  },
  {
    label: 'Delete spam',
    icon: 'lucide-trash',
    onClick: () => moderateReply(true),
    condition: () =>
      canModerate.value &&
      !props.comment.spam_removed_at &&
      !props.comment.deleted_at &&
      !props.readOnlyMode,
  },
  {
    label: 'Edit',
    icon: 'lucide-edit',
    onClick: () => startEditing(),
    condition: () =>
      !isEditing.value &&
      !isUpdating.value &&
      !props.comment.deleted_at &&
      !props.comment.hidden_at &&
      !props.comment.spam_removed_at &&
      !props.readOnlyMode &&
      canEditContent(props.comment, props.space, useSessionUser()),
  },
  {
    label: 'Revisions',
    icon: 'lucide-rotate-ccw',
    onClick: () => (showRevisionsDialog.value = true),
    condition: () =>
      !props.readOnlyMode &&
      !isAnonymousVisitor() &&
      !props.comment.hidden_at &&
      !props.comment.spam_removed_at &&
      Boolean(props.comment.edited_at),
  },
  {
    label: 'Copy link',
    icon: 'lucide-link',
    onClick: () => copyLink(props.comment),
  },
  {
    label: 'Bookmark',
    icon: 'lucide-bookmark',
    onClick: () => runBookmark('add_bookmark'),
    condition: () => Boolean(props.bookmarks) && !isBookmarked.value && !props.comment.deleted_at,
  },
  {
    label: 'Remove Bookmark',
    icon: 'lucide-bookmark',
    onClick: () => runBookmark('remove_bookmark'),
    condition: () => isBookmarked.value,
  },
  {
    label: 'Delete',
    icon: 'lucide-trash',
    onClick: () => {
      dialog.danger({
        title: 'Delete comment',
        message: 'Are you sure you want to delete this comment?',
        onConfirm: () => props.comments.delete.submit({ name: props.comment.name }),
      })
    },
    condition: () =>
      !isEditing.value &&
      !isUpdating.value &&
      canDeleteContent(props.comment, props.space, useSessionUser()) &&
      props.comment.deleted_at == null &&
      !props.comment.hidden_at &&
      !props.comment.spam_removed_at &&
      !props.readOnlyMode,
  },
])
</script>
