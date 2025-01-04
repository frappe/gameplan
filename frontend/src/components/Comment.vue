<template>
  <div
    class="pb-16 transition-shadow"
    :class="{
      ring: !editableComment?.setValue.loading && highlight,
    }"
    :data-id="comment.name"
  >
    <UserInfo :email="comment.owner" v-slot="{ user }">
      <div
        class="flex items-center text-base text-ink-gray-9 sticky top-0 pt-14 pb-2 bg-surface-white z-[1]"
      >
        <UserProfileLink class="mr-3" :user="user.name">
          <UserAvatar size="lg" :user="user.name" />
        </UserProfileLink>
        <div class="md:flex md:items-center">
          <UserProfileLink class="font-medium hover:text-ink-blue-3" :user="user.name">
            {{ user.full_name }}
            <span class="hidden md:inline">&nbsp;&middot;&nbsp;</span>
          </UserProfileLink>
          <div>
            <time
              class="text-ink-gray-5"
              :datetime="comment.creation"
              :title="$dayjs(comment.creation)"
            >
              {{ $dayjs(comment.creation).fromNow() }}
            </time>
            <span
              v-if="comment.modified > comment.creation"
              class="text-ink-gray-5"
              :title="$dayjs(comment.modified)"
            >
              &nbsp;&middot; Edited
            </span>
            <span v-if="editableComment?.setValue.loading" class="italic text-ink-gray-5">
              &nbsp;&middot; Sending...
            </span>
            <div v-if="editableComment?.setValue.error">
              &nbsp;&middot;
              <span class="text-ink-red-4"> Error</span>
            </div>
          </div>
        </div>
        <Dropdown
          v-show="editableComment == null"
          class="ml-auto"
          placement="right"
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
              editableComment,
          }"
          @keydown.ctrl.enter.capture.stop="updateComment(comment)"
          @keydown.meta.enter.capture.stop="updateComment(comment)"
        >
          <CommentEditor
            v-if="comment.deleted_at == null"
            :value="editableComment?.doc.content || comment.content"
            @change="
              (value) => {
                if (editableComment) {
                  editableComment.doc.content = value
                }
              }
            "
            :editable="editableComment != null"
            :submitButtonProps="{
              onClick: () => updateComment(comment),
              loading: editableComment?.setValue.loading,
            }"
            :discardButtonProps="{
              onClick: () => setEditing(comment.name, false),
            }"
          />
          <span class="text-base italic text-ink-gray-5" v-else> This message is deleted </span>
          <div class="mt-3" v-if="!comment.deleted_at && !editableComment && comment.reactions">
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
import { Dropdown } from 'frappe-ui'
import { useList } from 'frappe-ui/src/data-fetching'
import { copyToClipboard } from '@/utils'
import UserProfileLink from './UserProfileLink.vue'
import CommentEditor from './CommentEditor.vue'
import Reactions from './Reactions.vue'
import RevisionsDialog from './RevisionsDialog.vue'
import UserAvatar from './UserAvatar.vue'
import { GPComment } from '@/types/doctypes'
import { isSessionUser } from '@/data/session'
import { createDialog } from '@/utils/dialogs'

interface Props {
  comment: GPComment
  readOnlyMode?: boolean
  highlight?: boolean
  comments: ReturnType<typeof useList<GPComment>>
}

const props = defineProps<Props>()
const showRevisionsDialog = ref(false)
const editableComment = ref<ReturnType<typeof props.comments.edit> | null>(null)

const setEditing = (name: string, value: boolean) => {
  if (value) {
    editableComment.value = props.comments.edit(name)
  } else {
    editableComment.value = null
  }
}

const updateComment = (comment: GPComment) => {
  editableComment.value?.update().then(() => {
    setEditing(comment.name, false)
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
    onClick: () => setEditing(props.comment.name, true),
    condition: () => !props.comment.deleted_at && !props.readOnlyMode,
  },
  {
    label: 'Revisions',
    icon: 'rotate-ccw',
    onClick: () => (showRevisionsDialog.value = true),
    condition: () => props.comment.modified > props.comment.creation,
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
      createDialog({
        title: 'Delete comment',
        message: 'Are you sure you want to delete this comment?',
        actions: [
          {
            label: 'Delete',
            variant: 'solid',
            theme: 'red',
            onClick: ({ close }) => {
              return props.comments.setValue
                .submit({
                  name: props.comment.name,
                  deleted_at: $dayjs().format('YYYY-MM-DD HH:mm:ss'),
                })
                .then(close)
            },
          },
        ],
      })
    },
    condition: () =>
      isSessionUser(props.comment.owner) && props.comment.deleted_at == null && !props.readOnlyMode,
  },
])
</script>
