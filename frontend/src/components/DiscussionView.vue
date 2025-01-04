<template>
  <div class="relative flex h-full flex-col" v-if="postId && discussion.doc">
    <div class="mx-auto w-full max-w-3xl">
      <div class="pb-16">
        <div class="pb-2 pt-14 flex w-full items-center sticky top-0 z-[1] bg-surface-white">
          <UserProfileLink class="mr-3" :user="discussion.doc.owner">
            <UserAvatar size="lg" :user="discussion.doc.owner" />
          </UserProfileLink>
          <div class="flex flex-col md:block">
            <UserProfileLink
              class="text-base font-medium text-ink-gray-9 hover:text-ink-blue-3"
              :user="discussion.doc.owner"
            >
              {{ $user(discussion.doc.owner).full_name }}
              <span class="hidden md:inline text-ink-gray-8">&nbsp;&middot;&nbsp;</span>
            </UserProfileLink>
            <time
              class="text-base text-ink-gray-5"
              :datetime="discussion.doc.creation"
              :title="$dayjs(discussion.doc.creation).toString()"
            >
              {{ $dayjs(discussion.doc.creation).fromNow() }}
            </time>
          </div>
          <div class="ml-auto flex space-x-2">
            <Dropdown
              v-if="!readOnlyMode"
              class="ml-auto"
              placement="right"
              :button="{
                icon: 'more-horizontal',
                variant: 'ghost',
                label: 'Discussion Options',
              }"
              :options="actions"
            />
          </div>
        </div>
        <div :class="{ 'pb-4 mt-1': !editingPost }">
          <div class="flex items-start justify-between space-x-1">
            <h1 v-if="!editingPost" class="flex items-center text-2xl font-semibold">
              <Tooltip v-if="discussion.doc.closed_at" text="This discussion is closed">
                <LucideLock class="mr-2 h-4 w-4 text-ink-gray-7" :stroke-width="2" />
              </Tooltip>
              <span class="text-ink-gray-9">
                {{ discussion.doc.title }}
              </span>
            </h1>
          </div>
          <div class="mt-2 flex items-center text-base" v-show="!editingPost">
            <router-link
              class="text-ink-gray-8 hover:text-ink-gray-6"
              :to="{ name: 'Space', params: { spaceId: discussion.doc.project } }"
            >
              {{ space?.title }}
            </router-link>
            <span class="px-1.5 text-ink-gray-8">&middot;</span>
            <span class="text-ink-gray-5">
              {{
                discussion.doc.participants_count == 1
                  ? `1 participant`
                  : `${discussion.doc.participants_count} participants`
              }}
            </span>
          </div>
        </div>
        <div
          :class="{
            'rounded-lg border p-4 focus-within:border-outline-gray-3': editingPost,
          }"
        >
          <div v-if="editingPost" class="w-full">
            <div class="mb-2">
              <input
                v-if="editingPost"
                type="text"
                class="w-full rounded border-0 text-ink-gray-9 px-0 py-0.5 text-2xl font-semibold focus:ring-0"
                ref="title"
                v-model="discussion.doc.title"
                placeholder="Title"
                v-focus
              />
            </div>
          </div>
          <CommentEditor
            :value="discussion.doc.content"
            @change="discussion.doc.content = $event"
            :submitButtonProps="{
              variant: 'solid',
              onClick: () => {
                discussion.setValue.submit({
                  title: discussion.doc?.title,
                  content: discussion.doc?.content,
                })
                editingPost = false
              },
              loading: discussion.setValue.loading,
            }"
            :discardButtonProps="{
              onClick: () => {
                editingPost = false
                discussion.reload()
              },
            }"
            :editable="editingPost"
          />
        </div>
        <div class="mt-3">
          <Reactions
            doctype="GP Discussion"
            :name="discussion.doc.name"
            v-model:reactions="discussion.doc.reactions"
            :read-only-mode="readOnlyMode"
          />
        </div>
      </div>
      <CommentsArea
        doctype="GP Discussion"
        :name="discussion.doc.name"
        :newCommentsFrom="discussion.doc.last_unread_comment"
        :read-only-mode="readOnlyMode"
        :disable-new-comment="discussion.doc.closed_at"
      />
      <Dialog
        :options="{
          title: 'Move discussion to another project',
        }"
        @close="
          () => {
            discussionMoveDialog.project = null
            // discussion.moveToProject.reset()
          }
        "
        v-model="discussionMoveDialog.show"
      >
        <template #body-content>
          <Autocomplete
            :options="spaceOptions"
            v-model="discussionMoveDialog.project"
            placeholder="Select a project"
          />
          <ErrorMessage class="mt-2" :message="discussion.moveToProject.error" />
        </template>
        <template #actions>
          <Button
            class="w-full"
            variant="solid"
            :loading="discussion.moveToProject.loading"
            @click="moveToProject"
          >
            {{
              discussionMoveDialog.project
                ? `Move to ${discussionMoveDialog.project.label}`
                : 'Move'
            }}
          </Button>
        </template>
      </Dialog>
      <RevisionsDialog
        v-model="showRevisionsDialog"
        doctype="GP Discussion"
        :name="discussion.doc.name"
        fieldname="content"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onUnmounted, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Autocomplete, Dropdown, Dialog, Tooltip, usePageMeta } from 'frappe-ui'
import Reactions from './Reactions.vue'
import CommentsArea from '@/components/CommentsArea.vue'
import CommentEditor from './CommentEditor.vue'
import UserProfileLink from './UserProfileLink.vue'
import RevisionsDialog from './RevisionsDialog.vue'
import { focus as vFocus } from '@/directives'
import { copyToClipboard } from '@/utils'
import { useSpace } from '@/data/spaces'
import { useGroupedSpaces } from '@/data/groupedSpaces'
import { useDiscussion } from '@/data/discussions'
import { createDialog } from '@/utils/dialogs'

const props = defineProps<{
  postId: string
  readOnlyMode?: boolean
}>()

const router = useRouter()
const route = useRoute()

const editingPost = ref(false)
const discussionMoveDialog = reactive<{
  show: boolean
  project: { label: string; value: string } | null
}>({
  show: false,
  project: null,
})
const showRevisionsDialog = ref(false)

const discussion = useDiscussion(() => props.postId)

let removeOnSuccess = discussion.onSuccess((doc) => {
  updateUrlSlug()
  if (
    !route.query.comment &&
    !route.query.poll &&
    !route.query.fromSearch &&
    (doc.last_unread_comment || doc.last_unread_poll)
  ) {
    router.replace({
      query: {
        comment: doc.last_unread_comment || undefined,
        poll: doc.last_unread_poll || undefined,
      },
    })
  }

  if (route.name === 'Discussion' && route.params.postId === doc.name) {
    discussion.trackVisit.submit()
  }
})

onUnmounted(() => {
  removeOnSuccess()
})

// Methods
function copyLink() {
  let location = window.location
  let url = `${location.origin}${location.pathname}`
  copyToClipboard(url)
}

function moveToProject() {
  if (discussionMoveDialog.project?.value) {
    discussion.moveToProject
      .submit({
        project: discussionMoveDialog.project.value,
      })
      .then(() => {
        nextTick(() => {
          discussionMoveDialog.show = false
          discussionMoveDialog.project = null

          router.replace({
            name: 'Discussion',
            params: {
              spaceId: discussion.doc?.project,
              postId: discussion.doc?.name,
            },
          })
        })
      })
      .catch(() => {
        discussionMoveDialog.show = true
      })
  }
}

function updateUrlSlug() {
  let doc = discussion.doc
  if (!doc) return
  if (!route.params.slug || route.params.slug !== doc.slug) {
    nextTick(() => {
      router.replace({
        name: 'Discussion',
        params: { ...route.params, slug: doc.slug },
        query: route.query,
      })
    })
  }
}

const space = useSpace(() => discussion.doc?.project)

const spaceOptions = computed(() => {
  const groups = useGroupedSpaces().value
  return groups.map((group) => ({
    group: group.title,
    items: group.spaces.map((space) => ({
      label: space.title,
      value: space.name,
    })),
  }))
})

const actions = computed(() => [
  {
    label: 'Edit',
    icon: 'edit',
    onClick: () => {
      editingPost.value = true
    },
  },
  {
    label: 'Revisions',
    icon: 'rotate-ccw',
    onClick: () => (showRevisionsDialog.value = true),
  },
  {
    label: 'Copy link',
    icon: 'link',
    onClick: copyLink,
  },
  {
    label: 'Pin discussion...',
    icon: 'arrow-up-left',
    condition: () => !discussion.doc?.pinned_at,
    onClick: () => {
      createDialog({
        title: 'Pin discussion',
        message: `When a discussion is pinned, it shows up on top of the discussion list in ${space.value?.title}. Do you want to pin this discussion?`,
        icon: { name: 'arrow-up-left' },
        actions: [
          {
            label: 'Pin',
            onClick: ({ close }) => discussion.pinDiscussion.submit().then(close),
            variant: 'solid',
          },
        ],
      })
    },
  },
  {
    label: 'Unpin discussion...',
    icon: 'arrow-down-left',
    condition: () => discussion.doc?.pinned_at,
    onClick: () => {
      createDialog({
        title: 'Unpin discussion',
        message: `Do you want to unpin this discussion?`,
        icon: { name: 'arrow-down-left' },
        actions: [
          {
            label: 'Unpin',
            onClick: ({ close }) => discussion.unpinDiscussion.submit().then(close),
            variant: 'solid',
          },
        ],
      })
    },
  },
  {
    label: 'Close discussion...',
    icon: 'lock',
    condition: () => !discussion.doc?.closed_at,
    onClick: () => {
      createDialog({
        title: 'Close discussion',
        message:
          'When a discussion is closed, commenting is disabled. Anyone can re-open the discussion later. Do you want to close this discussion?',
        icon: { name: 'lock' },
        actions: [
          {
            label: 'Close',
            onClick: ({ close }) => discussion.closeDiscussion.submit().then(close),
            variant: 'solid',
          },
        ],
      })
    },
  },
  {
    label: 'Re-open discussion...',
    icon: 'unlock',
    condition: () => discussion.doc?.closed_at,
    onClick: () => {
      createDialog({
        title: 'Re-open discussion',
        message: 'Do you want to re-open this discussion? Anyone can comment on it again.',
        icon: { name: 'unlock' },
        actions: [
          {
            label: 'Re-open',
            onClick: ({ close }) => discussion.reopenDiscussion.submit().then(close),
            variant: 'solid',
          },
        ],
      })
    },
  },
  {
    label: 'Bookmark',
    icon: 'bookmark',
    onClick: () => discussion.addBookmark.submit(),
    condition: () => !discussion.doc?.is_bookmarked,
  },
  {
    label: 'Remove Bookmark',
    icon: 'bookmark',
    onClick: () => discussion.removeBookmark.submit(),
    condition: () => discussion.doc?.is_bookmarked,
  },
  {
    label: 'Move to...',
    icon: 'log-out',
    onClick: () => {
      discussionMoveDialog.show = true
    },
  },
  {
    label: 'Delete',
    icon: 'trash',
    onClick: () => {
      createDialog({
        title: 'Delete',
        message: 'Are you sure you want to delete this post? This is irreversible!',
        actions: [
          {
            label: 'Delete',
            variant: 'solid',
            theme: 'red',
            onClick: ({ close }) => {
              return discussion.delete.submit().then(() => {
                router.replace({ name: 'Space' })
                close()
              })
            },
          },
        ],
      })
    },
  },
])

// Page Meta
usePageMeta(() => {
  if (!discussion.doc) return
  let space = useSpace(() => discussion.doc?.project)
  if (!space) return
  return {
    title: [discussion.doc.title, space.value?.title].filter(Boolean).join(' - '),
  }
})
</script>
