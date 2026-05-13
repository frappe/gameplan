<template>
  <div class="relative" :data-id="comment.name">
    <div
      v-if="highlight"
      class="absolute inset-0 translate-y- z-[5] rounded border-2 -mx-4 -mb-4 mt-11 pointer-events-none"
    />
    <UserInfo :email="comment.owner" v-slot="{ user }">
      <div
        class="flex items-center text-base text-ink-gray-8 sticky top-0 pt-14 pb-2 bg-surface-white z-[1]"
      >
        <UserProfileLink class="mr-3" :user="user.name">
          <UserAvatarWithHover size="lg" :user="user.name" />
        </UserProfileLink>
        <div class="md:flex md:items-center">
          <UserProfileLink class="font-medium hover:text-ink-blue-4" :user="user.name">
            {{ user.full_name }}
            <span class="hidden md:inline">&nbsp;&middot;&nbsp;</span>
          </UserProfileLink>
          <div>
            <Tooltip :text="dayjsLocal(comment.creation).format('D MMM YYYY [at] h:mm A')">
              <time class="text-ink-gray-5" :datetime="comment.creation">
                {{ dayjsLocal(comment.creation).fromNow() }}
              </time>
            </Tooltip>
            <Tooltip
              v-if="comment.edited_at"
              :text="dayjsLocal(comment.edited_at).format('D MMM YYYY [at] h:mm A')"
            >
              <span class="text-ink-gray-5"> &nbsp;&middot; Edited </span>
            </Tooltip>
            <span v-if="isUpdating" class="italic text-ink-gray-5">
              &nbsp;&middot; Sending...
            </span>
            <div v-if="updateError">
              &nbsp;&middot;
              <span class="text-ink-red-4"> Error</span>
            </div>
          </div>
        </div>
        <Dropdown
          v-show="!isEditing"
          class="ml-auto"
          align="end"
          :button="{
            icon: 'more-horizontal',
            variant: 'ghost',
            label: 'Comment Options',
          }"
          :options="dropdownOptions"
        />
      </div>
      <div class="flex-1">
        <div
          :class="{
            'w-full rounded-lg border bg-surface-white p-4 focus-within:border-outline-gray-3':
              isEditing,
          }"
          @keydown.ctrl.enter.capture.stop="updateComment()"
          @keydown.meta.enter.capture.stop="updateComment()"
        >
          <CommentEditor
            v-if="comment.deleted_at == null"
            :value="isEditing ? draftContent : comment.content"
            @change="
              (value: string) => {
                if (isEditing) {
                  draftContent = value
                }
              }
            "
            :editable="isEditing"
            :submitButtonProps="{
              onClick: () => updateComment(),
              loading: isUpdating,
            }"
            :discardButtonProps="{
              onClick: () => discardEdit(),
            }"
            @rich-quote="$emit('rich-quote', $event)"
            @rich-quote-click="$emit('rich-quote-click', $event)"
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
    </UserInfo>
    <RevisionsDialog
      v-model="showRevisionsDialog"
      doctype="GP Comment"
      :name="comment.name"
      fieldname="content"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Dropdown, Tooltip, dayjsLocal } from 'frappe-ui'
import { useList } from 'frappe-ui'
import { copyToClipboard } from '@/utils'
import UserProfileLink from './UserProfileLink.vue'
import CommentEditor from './CommentEditor.vue'
import Reactions from './Reactions.vue'
import RevisionsDialog from './RevisionsDialog.vue'
import UserAvatarWithHover from './UserAvatarWithHover.vue'
import { GPComment } from '@/types/doctypes'
import { isSessionUser } from '@/data/session'
import { dialog } from 'frappe-ui'
import { tags } from '@/data/tags'

interface Props {
  comment: GPComment
  readOnlyMode?: boolean
  highlight?: boolean
  comments: ReturnType<typeof useList<GPComment>>
}

const props = defineProps<Props>()
const showRevisionsDialog = ref(false)
const isEditing = ref(false)
const draftContent = ref('')
const isUpdating = ref(false)
const updateError = ref(null)

const startEditing = () => {
  isEditing.value = true
  draftContent.value = props.comment.content
}

const discardEdit = () => {
  isEditing.value = false
  draftContent.value = ''
  updateError.value = null
}

const updateComment = () => {
  if (!draftContent.value.trim()) return

  isUpdating.value = true
  updateError.value = null

  props.comments.setValue
    .submit({
      name: props.comment.name,
      content: draftContent.value,
    })
    .then(() => {
      discardEdit()
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
    icon: 'edit',
    onClick: () => startEditing(),
    condition: () => !props.comment.deleted_at && !props.readOnlyMode,
  },
  {
    label: 'Revisions',
    icon: 'rotate-ccw',
    onClick: () => (showRevisionsDialog.value = true),
    condition: () => Boolean(props.comment.edited_at),
  },
  {
    label: 'Copy link',
    icon: 'link',
    onClick: () => copyLink(props.comment),
  },
  {
    label: 'Delete',
    icon: 'trash',
    onClick: () => {
      dialog.danger({
        title: 'Delete comment',
        message: 'Are you sure you want to delete this comment?',
        onConfirm: () => props.comments.delete.submit({ name: props.comment.name }),
      })
    },
    condition: () =>
      isSessionUser(props.comment.owner) && props.comment.deleted_at == null && !props.readOnlyMode,
  },
])
</script>
