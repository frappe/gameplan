<template>
  <div class="relative" :data-id="comment.name">
    <div
      v-if="highlight"
      class="absolute inset-0 translate-y- z-[5] rounded border-2 -mx-4 -mb-4 mt-11 pointer-events-none"
    />
    <div
      class="sticky -top-px z-[1] flex items-center bg-surface-base pb-2 pt-2 text-md text-ink-gray-8 sm:top-0 sm:pt-14 sm:text-base"
    >
      <UserProfileLink class="mr-3" :user="author.name">
        <UserAvatarWithHover class="sm:hidden" size="xl" :user="author.name" />
        <UserAvatarWithHover class="hidden sm:inline-flex" size="lg" :user="author.name" />
      </UserProfileLink>
      <div class="md:flex md:items-center">
        <UserProfileLink
          class="text-md-medium hover:text-ink-blue-8 sm:text-base sm:font-medium"
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
          <div v-if="updateError">
            &nbsp;&middot;
            <span class="text-ink-red-8"> Error</span>
          </div>
        </div>
      </div>
      <Dropdown
        v-show="!isEditing"
        class="ml-auto print:hidden"
        align="end"
        :button="{
          icon: 'lucide-more-horizontal',
          variant: 'ghost',
          label: 'Comment Options',
        }"
        :options="dropdownOptions"
      />
    </div>
    <div class="flex-1">
      <div
        :class="{
          'w-full rounded-lg border bg-surface-base p-4 focus-within:border-outline-gray-3':
            isEditing,
        }"
        @keydown.ctrl.enter.capture.stop="updateComment()"
        @keydown.meta.enter.capture.stop="updateComment()"
      >
        <CommentEditor
          v-if="comment.deleted_at == null"
          :quote-source-id="`comment:${comment.name}`"
          :author="comment.owner"
          :value="isEditing ? draftData.content : comment.content"
          @change="onEditorChange"
          :editable="isEditing"
          :submitButtonProps="{
            onClick: () => updateComment(),
            loading: isUpdating,
          }"
          :discardButtonProps="{
            onClick: () => discardEdit(),
          }"
        />
        <span class="text-base italic text-ink-gray-5" v-else> This message is deleted </span>
        <div class="mt-3" v-if="!comment.deleted_at && !isEditing && comment.reactions">
          <Reactions
            doctype="GP Comment"
            :name="comment.name"
            v-model:reactions="comment.reactions"
            :read-only-mode="readOnlyMode"
          />
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
import { ref, computed, defineAsyncComponent } from 'vue'
import { Dropdown, Tooltip, dayjsLocal } from 'frappe-ui'
import { useList } from 'frappe-ui'
import { copyToClipboard } from '@/utils'
import UserProfileLink from './UserProfileLink.vue'
import CommentEditor from './editor/CommentEditor.vue'
import Reactions from './Reactions.vue'
// Lazy: htmldiff-js + motion-v only load when a viewer opens edit history.
const RevisionsDialog = defineAsyncComponent(() => import('./RevisionsDialog.vue'))
import UserAvatarWithHover from './UserAvatarWithHover.vue'
import { GPComment } from '@/types/doctypes'
import { dialog } from 'frappe-ui'
import { tags } from '@/data/tags'
import { useDraftSync } from '@/data/useDraftSync'
import { useUser, useSessionUser } from '@/data/users'
import type { Space } from '@/data/spaces'
import { canDeleteContent, canEditContent } from '@/utils/permissions'

interface Props {
  comment: GPComment
  readOnlyMode?: boolean
  highlight?: boolean
  comments: ReturnType<typeof useList<GPComment>>
  // Space the comment's thread belongs to, for community-admin delete moderation.
  space?: Space | null
}

const props = defineProps<Props>()
const showRevisionsDialog = ref(false)
const isEditing = ref(false)
const isUpdating = ref(false)
const updateError = ref(null)
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

const onEditorChange = (value: string) => {
  if (isEditing.value) draftData.value.content = value
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
  const content = draftData.value.content
  if (!content?.trim()) return

  isUpdating.value = true
  updateError.value = null

  props.comments.setValue
    .submit({
      name: props.comment.name,
      content,
    })
    .then(async () => {
      await draft.commit()
      isEditing.value = false
      tags.reload()
    })
    .catch((error) => {
      updateError.value = error
    })
    .finally(() => {
      isUpdating.value = false
    })
}

const copyLink = (comment: GPComment) => {
  const location = window.location
  const url = `${location.origin}${location.pathname}?comment=${comment.name}`
  copyToClipboard(url)
}

const dropdownOptions = computed(() => [
  {
    label: 'Edit',
    icon: 'lucide-edit',
    onClick: () => startEditing(),
    condition: () =>
      !props.comment.deleted_at &&
      !props.readOnlyMode &&
      canEditContent(props.comment, props.space, useSessionUser()),
  },
  {
    label: 'Revisions',
    icon: 'lucide-rotate-ccw',
    onClick: () => (showRevisionsDialog.value = true),
    condition: () => Boolean(props.comment.edited_at),
  },
  {
    label: 'Copy link',
    icon: 'lucide-link',
    onClick: () => copyLink(props.comment),
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
      canDeleteContent(props.comment, props.space, useSessionUser()) &&
      props.comment.deleted_at == null &&
      !props.readOnlyMode,
  },
])
</script>
