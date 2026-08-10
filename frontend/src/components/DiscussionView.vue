<template>
  <div class="relative flex h-full flex-col" v-if="postId">
    <PageHeaderMobile class="sm:hidden" :title="mobileHeaderTitle">
      <template #left>
        <PageHeaderBackButton :to="backRoute" />
      </template>
    </PageHeaderMobile>
    <PageHeader class="hidden sm:flex">
      <SpaceBreadcrumbs
        class="flex"
        :spaceId="currentSpaceId"
        :items="[{ label: discussion.doc?.title || postId, onClick: scrollToTop }]"
      />
    </PageHeader>
    <div class="discussion-container">
      <div v-if="discussion.loading">
        <div
          class="sticky -top-px z-[1] flex w-full items-center bg-surface-base pb-2 pt-2 sm:top-0 sm:pt-14"
        >
          <Avatar size="xl" label="A" class="mr-3 shrink-0 animate-pulse sm:hidden">
            <div></div>
          </Avatar>
          <Avatar size="lg" label="A" class="mr-3 hidden shrink-0 animate-pulse sm:inline-flex">
            <div></div>
          </Avatar>
          <div class="flex flex-col md:block">
            <div class="text-base-medium bg-surface-gray-2 animate-pulse w-20 h-4"></div>
          </div>
          <div class="ml-auto flex space-x-2">
            <Button>
              <template #icon>
                <div class="animate-pulse w-20 h-8"></div>
              </template>
            </Button>
          </div>
        </div>
        <div class="flex items-start justify-between space-x-1">
          <h1 class="flex items-center text-4xl-semibold animate-pulse">
            <span class="bg-surface-gray-3 h-5.5 w-32"> </span>
            <span class="bg-surface-gray-3 h-5.5 w-20 ml-2"> </span>
            <span class="bg-surface-gray-3 h-5.5 w-40 ml-2"> </span>
          </h1>
        </div>
      </div>
      <template v-else-if="discussion.doc">
        <div
          :class="{
            'rounded-6 border mt-14 py-4 px-3 sm:px-5 -mx-3 sm:-mx-5 focus-within:border-outline-gray-3':
              editingPost,
          }"
          @keydown.ctrl.enter.capture.stop="updatePost"
          @keydown.meta.enter.capture.stop="updatePost"
          @keydown.esc="cancelEdit"
        >
          <div
            class="flex w-full items-center bg-surface-base pb-2 pt-2"
            :class="editingPost ? 'sm:pt-0' : 'sticky -top-px z-[1] sm:top-0 sm:pt-14'"
          >
            <UserProfileLink class="mr-3" :user="discussion.doc.owner">
              <UserAvatarWithHover class="sm:hidden" size="xl" :user="discussion.doc.owner" />
              <UserAvatarWithHover
                class="hidden sm:inline-flex"
                size="lg"
                :user="discussion.doc.owner"
              />
            </UserProfileLink>
            <div class="flex flex-col md:block">
              <UserProfileLink
                class="text-md-medium text-ink-gray-8 hover:text-ink-gray-9 sm:text-base-medium"
                :user="discussion.doc.owner"
              >
                {{ $user(discussion.doc.owner).full_name }}
                <span class="hidden md:inline text-ink-gray-7">&nbsp;&middot;&nbsp;</span>
              </UserProfileLink>
              <Tooltip :text="dayjsLocal(discussion.doc.creation).format('D MMM YYYY [at] h:mm A')">
                <time
                  class="text-p-base text-ink-gray-5 sm:text-base"
                  :datetime="discussion.doc.creation"
                >
                  {{ dayjsLocal(discussion.doc.creation).fromNow() }}
                </time>
              </Tooltip>
            </div>
            <div class="ml-auto flex space-x-2 print:hidden">
              <Dropdown
                v-if="!readOnlyMode"
                class="ml-auto"
                align="end"
                :button="{
                  icon: 'lucide-more-horizontal',
                  variant: 'ghost',
                  label: 'Discussion Options',
                }"
                :options="actions"
              />
            </div>
          </div>
          <div :class="{ 'pb-4 mt-1': !editingPost }">
            <div class="flex items-start justify-between space-x-1">
              <h1 v-if="!editingPost" class="flex items-center text-4xl-semibold" ref="postTitleEl">
                <Tooltip v-if="discussion.doc.closed_at" text="This discussion is closed">
                  <span class="lucide-lock mr-2 h-4 w-4 text-ink-gray-6" />
                </Tooltip>
                <span class="text-ink-gray-8">
                  {{ discussion.doc.title }}
                </span>
              </h1>
            </div>
            <div class="mt-2 flex items-center text-base" v-show="!editingPost">
              <span class="text-ink-gray-5">
                {{
                  discussion.doc.participants_count == 1
                    ? `1 participant`
                    : `${discussion.doc.participants_count} participants`
                }}
              </span>
              <template v-if="discussion.doc.views > 1">
                <span class="px-1.5 text-ink-gray-7">&middot;</span>
                <span class="text-ink-gray-5"> {{ discussion.doc.views }} views </span>
              </template>
            </div>
          </div>
          <div ref="mainPostContentEl" :aria-busy="isPostDraftLoading" :inert="isPostDraftLoading">
            <div v-if="isPostDraftLoading" role="status" class="mb-2 text-sm text-ink-gray-5">
              Loading draft…
            </div>
            <div v-if="editingPost" class="w-full">
              <div class="mb-2">
                <input
                  v-if="editingPost"
                  type="text"
                  class="w-full bg-transparent border-0 text-ink-gray-8 px-0 py-0.5 text-4xl-semibold focus:ring-0"
                  ref="title"
                  v-model="postDraftData.title"
                  placeholder="Title"
                  :disabled="isPostDraftLoading"
                />
              </div>
            </div>
            <!-- An empty body renders as nothing at all, which reads as a broken page rather
                 than an empty post. Say so explicitly. -->
            <p
              v-if="!editingPost && isEditorContentEmpty(discussion.doc.content)"
              class="text-p-base text-ink-gray-5"
            >
              This post has no content.
            </p>
            <DiscussionViewEditor
              ref="postEditor"
              :content="editingPost ? postDraftData.content : discussion.doc.content"
              :editable="editingPost && !isPostDraftLoading"
              :saving="discussion.setValue.loading"
              :can-save="canSavePost"
              :quote-source-id="`discussion:${discussion.doc.name}`"
              :author="discussion.doc.owner"
              @change="onPostEditorChange"
              @save="updatePost"
              @discard="cancelEdit"
            />
          </div>
          <div class="mt-3" v-show="!editingPost">
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
          :space="space"
          :newCommentsFrom="discussion.doc.last_unread_comment?.toString()"
          :read-only-mode="readOnlyMode"
          :disable-new-comment="Boolean(discussion.doc.closed_at)"
          :hide-new-comment="editingPost"
          :activity-version="discussion.doc.modified"
          ref="commentsArea"
        />
        <QuoteBacklinksPopover :store="richQuotes" @select="scrollToQuotingComment" />
        <Dialog
          title="Move discussion to another space"
          @close="
            () => {
              discussionMoveDialog.project = null
            }
          "
          v-model:open="discussionMoveDialog.show"
        >
          <Combobox
            :options="spaceOptions"
            v-model="discussionMoveDialog.project"
            placeholder="Select a project"
            class="w-full"
            autofocus
            open-on-click
          />
          <ErrorMessage class="mt-2" :message="discussion.moveToProject.error" />
          <template #actions>
            <Button
              class="w-full"
              variant="solid"
              :loading="discussion.moveToProject.loading"
              @click="moveToSpace"
            >
              {{
                discussionMoveDialog.project
                  ? `Move to ${useSpace(discussionMoveDialog.project).value?.title}`
                  : 'Move'
              }}
            </Button>
          </template>
        </Dialog>
        <Dialog
          title="Pin discussion"
          @close="
            () => {
              pinDialog.show = false
              pinDialog.pinToCategory = false
            }
          "
          v-model:open="pinDialog.show"
        >
          <p class="text-p-base text-ink-gray-6 mb-3">
            When a discussion is pinned, it shows up on top of the discussion list.
          </p>

          <div class="space-y-2">
            <label class="flex items-center justify-between">
              <div>
                <div class="text-base-medium text-ink-gray-9 mb-1">Pin to Community</div>
                <div class="text-sm text-ink-gray-5" v-if="pinDialog.pinToCategory">
                  Show in all {{ communityTitle }} discussions
                </div>
                <div class="text-sm text-ink-gray-5" v-else>Show in {{ space?.title }} only</div>
              </div>
              <Switch size="sm" v-model="pinDialog.pinToCategory" />
            </label>
          </div>
          <template #actions>
            <div class="flex">
              <Button
                class="ml-auto"
                variant="solid"
                :loading="discussion.pinDiscussion.loading"
                @click="
                  () => {
                    discussion.pinDiscussion
                      .submit({ pin_scope: pinDialog.pinToCategory ? 'Category' : 'Space' })
                      .then(() => {
                        pinDialog.show = false
                        pinDialog.pinToCategory = false
                      })
                  }
                "
              >
                Pin Discussion
              </Button>
            </div>
          </template>
        </Dialog>
        <RevisionsDialog
          v-model="showRevisionsDialog"
          doctype="GP Discussion"
          :name="discussion.doc.name"
          fieldname="content"
        />
      </template>
      <EmptyStateBox v-else-if="notFound" class="mx-auto mt-14 max-w-2xl px-6">
        <LucideTriangleAlert class="mb-3 size-7 text-ink-gray-4" />
        <div class="text-base text-ink-gray-7">Discussion not found</div>
        <p class="mt-2 max-w-md text-center text-p-sm text-ink-gray-5">
          This discussion may have been deleted, or you no longer have access to it. Refresh to try
          again.
        </p>
      </EmptyStateBox>
      <!-- Fetch finished, but there is no doc and no recognised not-found/forbidden error.
           Fail visibly instead of rendering a blank page. Gated on isFinished so the
           pre-fetch tick (useFetch defers its first execute by a microtask) doesn't flash
           an error. -->
      <EmptyStateBox v-else-if="discussion.isFinished" class="mx-auto mt-14 max-w-2xl px-6">
        <LucideTriangleAlert class="mb-3 size-7 text-ink-gray-4" />
        <div class="text-base text-ink-gray-7">Could not load this discussion</div>
        <p class="mt-2 max-w-md text-center text-p-sm text-ink-gray-5">
          Something went wrong while loading it. Refresh to try again.
        </p>
      </EmptyStateBox>
    </div>
    <div
      v-if="!isMobileViewport && !editingPost"
      class="fixed bottom-3 h-9 grid place-content-center right-3 z-[2] print:hidden"
    >
      <Button variant="ghost" v-show="isScrolled" @click="scrollToTop">
        <template #prefix>
          <span class="lucide-arrow-up h-5 w-5 text-ink-gray-6" />
        </template>
        Scroll to top
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  ref,
  computed,
  defineAsyncComponent,
  nextTick,
  onMounted,
  onBeforeUnmount,
  reactive,
  watch,
  useTemplateRef,
} from 'vue'
import { useRouter, useRoute, type RouteLocationRaw } from 'vue-router'
import {
  PageHeaderBackButton,
  PageHeaderMobile,
  PageHeader,
  Combobox,
  Avatar,
  Dropdown,
  Dialog,
  Tooltip,
  usePageMeta,
  dayjsLocal,
  Switch,
  dialog,
} from 'frappe-ui'
import { until } from '@vueuse/core'
import type { Editor } from '@tiptap/vue-3'
import Reactions from './Reactions.vue'
import UserAvatarWithHover from './UserAvatarWithHover.vue'
import CommentsArea from '@/components/CommentsArea.vue'
import DiscussionViewEditor from './editor/DiscussionViewEditor.vue'
import UserProfileLink from './UserProfileLink.vue'
// Lazy: htmldiff-js + motion-v only load when a viewer opens edit history.
const RevisionsDialog = defineAsyncComponent(() => import('./RevisionsDialog.vue'))
import SpaceBreadcrumbs from './SpaceBreadcrumbs.vue'
import EmptyStateBox from './EmptyStateBox.vue'
import { copyToClipboard, isEditorContentEmpty } from '@/utils'
import { getSpace, useSpace } from '@/data/spaces'
import { useCommunity } from '@/data/communities'
import { useGroupedSpaceOptions } from '@/data/groupedSpaces'
import { useDiscussion } from '@/data/discussions'
import { useDraftSync } from '@/data/useDraftSync'
import { tags } from '@/data/tags'
import { shellScrollContainer, useShellScrolled } from 'frappe-ui'
import { useIsMobile } from '@/utils/useIsMobile'
import { provideRichQuotes } from '@/components/RichQuoteExtension/useRichQuotes'
import QuoteBacklinksPopover from '@/components/RichQuoteExtension/QuoteBacklinksPopover.vue'
import { refreshUnreadCountForProjects } from '@/data/unreadCount'
import { useSessionUser } from '@/data/users'
import { canDeleteContent, canEditContent } from '@/utils/permissions'
import { useCommandPaletteCommands } from './CommandPalette/registry'
import { useOwnedRouteWrites } from '@/composables/useOwnedRouteWrites'

const props = defineProps<{
  postId: string
  readOnlyMode?: boolean
}>()

const router = useRouter()
const route = useRoute()
// This view also renders behind the settings overlay, where the URL belongs to /settings/*.
// Rewriting it from there would both throw (no postId param to spread) and navigate the app
// off the settings route, closing the dialog. A page may only rewrite a URL it owns.
const runWhenOwned = useOwnedRouteWrites(() => route.name === 'Discussion')
const isMobileViewport = useIsMobile()
const commentsArea = useTemplateRef('commentsArea')
const postEditor = useTemplateRef<{ editor: Editor | null }>('postEditor')
const mainPostContentEl = ref<HTMLElement | null>(null)
const postTitleEl = useTemplateRef<HTMLElement>('postTitleEl')

const isScrolled = useShellScrolled()
const scrollContainerEl = shellScrollContainer
function scrollToTop() {
  shellScrollContainer.value?.scrollTo({ top: 0, behavior: 'smooth' })
}
const discussion = useDiscussion(() => props.postId)
// In-app navigation skips the router's server canonicalization for speed, so a stale link to a
// discussion deleted or moved out of reach after local data loaded would otherwise render a blank
// detail view. Show a not-found state in place (keeping the URL) rather than redirecting to the
// NotFound route: the URL stays valid, so refreshing re-runs the load and recovers if access was
// only transiently denied (e.g. a just-joined community still propagating). Only a definitive
// missing/forbidden response counts — never a transient network/5xx error, which would wrongly
// bury a valid discussion.
const notFound = computed(() => isMissingOrForbidden(discussion.error))
function isMissingOrForbidden(error: unknown): boolean {
  // useDoc surfaces a FrappeResponseError whose `type` is the backend exception name (there's no
  // HTTP status on it). A deleted/never-existed doc is DoesNotExistError; one in a now-inaccessible
  // space is PermissionError. Anything else (network/5xx) is transient and must NOT bury a valid
  // discussion behind the not-found state.
  const type = (error as { type?: string } | null)?.type
  return type === 'DoesNotExistError' || type === 'PermissionError'
}
const showTitleInMobileHeader = ref(false)
const mobileHeaderTitle = computed(() =>
  showTitleInMobileHeader.value ? discussion.doc?.title || 'Discussion' : 'Discussion',
)

const richQuotes = provideRichQuotes()
richQuotes.setPostContentEl(() => mainPostContentEl.value)

function scrollToQuotingComment(commentId: string) {
  commentsArea.value?.scrollToCommentById(commentId)
}

const editingPost = ref(false)
// snapshot of title/content captured when edit mode opens, so we can detect
// unsaved changes and confirm before discarding them
const editSnapshot = ref<{ title: string; content: string } | null>(null)
const discussionMoveDialog = reactive<{
  show: boolean
  project: string | null
}>({
  show: false,
  project: null,
})
const pinDialog = reactive<{
  show: boolean
  pinToCategory: boolean
}>({
  show: false,
  pinToCategory: false,
})
const showRevisionsDialog = ref(false)

// While the post is being edited, its title/body live in an auto-saved draft instead of
// being mutated on discussion.doc directly. The draft survives reloads and navigation, and
// silently restores if the edit is reopened. Dormant until editingPost flips true.
const postDraft = useDraftSync({
  identity: () => ({
    type: 'Discussion',
    mode: 'Edit',
    referenceDoctype: 'GP Discussion',
    referenceName: props.postId,
  }),
  enabled: editingPost,
  initialPayload: () => ({
    title: discussion.doc?.title ?? '',
    content: discussion.doc?.content ?? '',
  }),
})
const postDraftData = postDraft.data
const isPostDraftLoading = postDraft.isLoading

function onPostEditorChange(value: string) {
  if (editingPost.value) postDraftData.value.content = value
}

// The scroll container is owned by the shell (Desktop/MobileShell) and registers
// asynchronously — and re-registers across desktop↔mobile layout swaps — so bind the
// scroll listener reactively as the element becomes available rather than once at mount.
watch(
  scrollContainerEl,
  (el, prev) => {
    prev?.removeEventListener('scroll', updateMobileHeaderTitle)
    el?.addEventListener('scroll', updateMobileHeaderTitle)
    updateMobileHeaderTitle()
  },
  { immediate: true },
)

onMounted(() => {
  scrollToUnread()
})

onBeforeUnmount(() => {
  scrollContainerEl.value?.removeEventListener('scroll', updateMobileHeaderTitle)
})

function updateMobileHeaderTitle() {
  if (!isMobileViewport.value) {
    showTitleInMobileHeader.value = false
    return
  }

  const titleElement = postTitleEl.value
  if (!titleElement || editingPost.value) {
    showTitleInMobileHeader.value = false
    return
  }

  const scrollContainer = scrollContainerEl.value
  if (!scrollContainer) return
  const containerTop = scrollContainer.getBoundingClientRect().top
  const mobileHeaderHeight = parseFloat(
    getComputedStyle(document.documentElement).getPropertyValue('--mobile-header-height'),
  )

  showTitleInMobileHeader.value =
    titleElement.getBoundingClientRect().bottom <= containerTop + mobileHeaderHeight
}

watch([() => discussion.doc?.title, editingPost, isMobileViewport], () => {
  nextTick(updateMobileHeaderTitle)
})

async function scrollToUnread() {
  if (!discussion.doc) {
    // Wait for the doc to load, but give up the moment it resolves to missing/forbidden — both so
    // we don't await a doc that will never arrive, and so we stop reading the errored resource
    // (which throws once its store entry is dropped). notFound is checked first so the `||`
    // short-circuits before touching discussion.doc when the fetch failed.
    await until(() => notFound.value || Boolean(discussion.doc)).toBeTruthy()
    if (notFound.value || !discussion.doc) return
  }

  canonicalizeRoute()

  let doc = discussion.doc
  if (
    route.name === 'Discussion' &&
    !route.query.comment &&
    !route.query.poll &&
    !route.query.fromSearch &&
    (doc?.last_unread_comment || doc?.last_unread_poll)
  ) {
    if (doc.last_unread_comment) {
      router.replace({
        query: {
          comment: doc.last_unread_comment || undefined,
        },
      })
    } else if (doc.last_unread_poll) {
      router.replace({
        query: {
          poll: doc.last_unread_poll || undefined,
        },
      })
    }
  }

  if (route.name === 'Discussion' && route.params.postId === doc?.name) {
    discussion.trackVisit.submit().then(() => {
      refreshUnreadCountForProjects([doc.project])
    })
  }
}

// Methods
function copyLink() {
  let location = window.location
  let url = `${location.origin}${location.pathname}`
  copyToClipboard(url)
}

// Cold-load fallback only: PageHeaderBackButton walks history when there is any.
// Undefined leaves it with nothing to recover to, which is right for a discussion
// reached without a community in the URL.
const backRoute = computed<RouteLocationRaw | undefined>(() => {
  const communityId = routeParam(route.params.communityId)
  const spaceId = routeParam(route.params.spaceId)

  if (communityId && spaceId) {
    return { name: 'SpaceDiscussions', params: { communityId, spaceId } }
  }
  if (communityId) {
    return { name: 'Discussions', params: { communityId } }
  }
  return undefined
})

function routeParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value
}

function moveToSpace() {
  const targetSpace = discussionMoveDialog.project
  if (targetSpace) {
    discussion.moveToProject
      .submit({
        project: targetSpace,
      })
      .then(() => {
        nextTick(() => {
          discussionMoveDialog.show = false
          discussionMoveDialog.project = null

          // Route to the space we asked for, not the one read back off the doc: the doc's
          // refetch lands after this callback, so reading discussion.doc.project here still
          // returns the old space and the URL stays on it - leaving the sidebar highlighting
          // a space the discussion no longer belongs to.
          //
          // The slug has to be passed too. A move never changes it, but the canonical-route
          // guard treats a missing slug as "not canonical yet" and falls back to fetching the
          // discussion from the server - a request it memoizes for a second, so a move made
          // soon after the page loaded is answered with the pre-move copy and the URL bounces
          // straight back to the old space.
          router.replace({
            name: 'Discussion',
            params: {
              communityId: getSpace(targetSpace)?.team,
              spaceId: targetSpace,
              postId: discussion.doc?.name,
              slug: route.params.slug,
            },
          })
        })
      })
      .catch(() => {
        discussionMoveDialog.show = true
      })
  }
}

// A post needs both halves: saving an empty body over a real one leaves a post that renders
// as a blank page for everyone, with no way back except the revision history.
const canSavePost = computed(
  () =>
    Boolean(postDraftData.value.title?.trim()) &&
    !isEditorContentEmpty(postDraftData.value.content),
)

// Read content from the editor's own serializer rather than discussion.doc.content:
// the editor re-normalizes HTML on load and writes it back, so the stored value
// drifts from the server copy without any user edit. Comparing getHTML() to
// getHTML() keeps both sides on the same normalization.
function currentPostContent() {
  return postEditor.value?.editor?.getHTML() ?? discussion.doc?.content ?? ''
}

function startEditingPost() {
  editSnapshot.value = {
    title: discussion.doc?.title ?? '',
    content: currentPostContent(),
  }
  editingPost.value = true
  // The options dropdown restores focus to its trigger as it closes, which would
  // otherwise swallow the editor focus (and the Esc/⌘+Enter shortcuts). Focus the
  // editor on the next frame, after that restore has settled.
  nextTick(() => {
    requestAnimationFrame(() => postEditor.value?.editor?.commands.focus())
  })
}

function isPostDirty() {
  if (!editSnapshot.value) return false
  return (
    (postDraftData.value.title ?? '') !== editSnapshot.value.title ||
    currentPostContent() !== editSnapshot.value.content
  )
}

function closeEditor() {
  editingPost.value = false
  editSnapshot.value = null
  // Explicit discard throws the draft away (navigating away would keep it instead).
  postDraft.clear()
  discussion.reload()
}

function cancelEdit() {
  if (!editingPost.value) return
  if (isPostDirty()) {
    dialog.danger({
      title: 'Discard changes',
      message: 'You have unsaved changes. Are you sure you want to discard them?',
      confirmLabel: 'Discard changes',
      cancelLabel: 'Keep editing',
      onConfirm: closeEditor,
    })
  } else {
    closeEditor()
  }
}

function updatePost() {
  if (!editingPost.value || !canSavePost.value) return
  discussion.setValue
    .submit({
      title: postDraftData.value.title,
      content: postDraftData.value.content,
    })
    .then(async () => {
      // Content is saved onto the post; migrate the draft's attachments and delete it.
      await postDraft.commit()
      tags.reload()
    })
  editingPost.value = false
  editSnapshot.value = null
}

// Runs once per visit, when the doc resolves — so if the URL is not ours at that moment,
// the correction has to wait for it rather than be dropped for the rest of the visit.
function canonicalizeRoute() {
  runWhenOwned(applyCanonicalRoute)
}

function applyCanonicalRoute() {
  let doc = discussion.doc
  if (!doc) return

  // A discussion moved to another space keeps its postId, so an in-app link (which the router
  // fast path trusts without a server check) can land on a stale spaceId/communityId. Rewrite
  // to the document's real space here so route params — and the actions that read them, like
  // creating from the space context — target the current space, not the old one.
  const canonicalSpaceId = doc.project
  const canonicalCommunityId = canonicalSpaceId ? getSpace(canonicalSpaceId)?.team : undefined
  // Only rewrite the space when its community resolves locally too — otherwise we'd strand the
  // new spaceId under the old communityId. If the space isn't cached yet, leave the route as-is
  // (the slug is independent and always safe to correct).
  //
  // KNOWN LIMITATION: when the destination space is NOT in the local cache, the route keeps the
  // stale spaceId/communityId. The discussion body still renders (it reads doc.project directly),
  // but route-param-derived actions (e.g. "new discussion in this space", sidebar active-space)
  // target the OLD space until the new one happens to be cached. Self-corrects on a refresh, which
  // routes through the server canonicalization. Acceptable because moving a discussion is rare and
  // the alternative (stranding the new space under the wrong community) is worse. If this becomes a
  // real problem, fetch the destination space here instead of relying on it already being cached.
  // Spaces autoname to integers, so doc.project arrives as a number while route params are
  // always strings - compare them as strings or every load looks like a mismatch.
  const spaceMismatch =
    canonicalSpaceId &&
    canonicalCommunityId &&
    routeParam(route.params.spaceId) !== String(canonicalSpaceId)
  const slugMismatch = !route.params.slug || route.params.slug !== doc.slug
  if (!spaceMismatch && !slugMismatch) return

  nextTick(() => {
    router.replace({
      name: 'Discussion',
      params: {
        ...route.params,
        ...(spaceMismatch ? { communityId: canonicalCommunityId, spaceId: canonicalSpaceId } : {}),
        slug: doc.slug,
      },
      query: route.query,
    })
  })
}

const space = useSpace(() => discussion.doc?.project)
const community = useCommunity(() => discussion.doc?.team)
const communityTitle = computed(() => community.value?.title ?? '')
const currentSpaceId = computed(() => {
  if (discussion.doc?.project) return discussion.doc.project
  if (typeof route.params.spaceId === 'string') return route.params.spaceId
  return ''
})

const spaceOptions = useGroupedSpaceOptions({
  filterFn: (space) => !space.archived_at && space.name !== discussion.doc?.project,
})

// Edit and the lifecycle actions (pin/close/move) all change the post itself, so
// they follow the same business rule as editing — hidden from guests on posts they
// don't own. Mirrors backend can_edit_content (see utils/permissions.ts).
const canEditDiscussion = computed(() =>
  canEditContent(discussion.doc, space.value, useSessionUser()),
)

const actions = computed(() => [
  {
    label: 'Edit',
    icon: 'lucide-edit',
    onClick: startEditingPost,
    condition: () => canEditDiscussion.value,
  },
  {
    label: 'Revisions',
    icon: 'lucide-rotate-ccw',
    onClick: () => (showRevisionsDialog.value = true),
  },
  {
    label: 'Copy link',
    icon: 'lucide-link',
    onClick: copyLink,
  },
  {
    label: 'Mark as unread',
    icon: 'lucide-mail',
    onClick: () => {
      discussion.markAsUnread.submit().then(() => {
        if (discussion.doc?.project) {
          refreshUnreadCountForProjects([discussion.doc.project])
        }
      })
    },
  },
  {
    label: 'Bookmark',
    icon: 'lucide-bookmark',
    onClick: () => discussion.addBookmark.submit(),
    condition: () => !discussion.doc?.is_bookmarked,
  },
  {
    label: 'Pin discussion...',
    icon: 'lucide-arrow-up-left',
    condition: () => canEditDiscussion.value && !discussion.doc?.pinned_at,
    onClick: () => {
      pinDialog.show = true
    },
  },
  {
    label: 'Unpin discussion...',
    icon: 'lucide-arrow-down-left',
    condition: () => canEditDiscussion.value && !!discussion.doc?.pinned_at,
    onClick: () => {
      const pinScope = discussion.doc?.pin_scope
      const scopeText =
        pinScope === 'Category'
          ? `This discussion is pinned across the ${communityTitle.value} community.`
          : `This discussion is pinned in ${space.value?.title} only.`

      dialog.confirm({
        title: 'Unpin discussion',
        message: `${scopeText} Do you want to unpin it?`,
        icon: 'lucide-arrow-down-left',
        confirmLabel: 'Unpin',
        onConfirm: () => discussion.unpinDiscussion.submit(),
      })
    },
  },
  {
    label: 'Close discussion...',
    icon: 'lucide-lock',
    condition: () => canEditDiscussion.value && !discussion.doc?.closed_at,
    onClick: () => {
      dialog.confirm({
        title: 'Close discussion',
        message:
          'When a discussion is closed, commenting is disabled. Anyone can re-open the discussion later. Do you want to close this discussion?',
        icon: 'lucide-lock',
        confirmLabel: 'Close',
        onConfirm: () => discussion.closeDiscussion.submit(),
      })
    },
  },
  {
    label: 'Re-open discussion...',
    icon: 'lucide-unlock',
    condition: () => canEditDiscussion.value && !!discussion.doc?.closed_at,
    onClick: () => {
      dialog.confirm({
        title: 'Re-open discussion',
        message: 'Do you want to re-open this discussion? Anyone can comment on it again.',
        icon: 'lucide-unlock',
        confirmLabel: 'Re-open',
        onConfirm: () => discussion.reopenDiscussion.submit(),
      })
    },
  },
  {
    label: 'Remove Bookmark',
    icon: 'lucide-bookmark',
    onClick: () => discussion.removeBookmark.submit(),
    condition: () => discussion.doc?.is_bookmarked,
  },
  {
    label: 'Move to...',
    icon: 'lucide-log-out',
    condition: () => canEditDiscussion.value,
    onClick: () => {
      discussionMoveDialog.show = true
    },
  },
  {
    label: 'Delete',
    icon: 'lucide-trash',
    condition: () => canDeleteContent(discussion.doc, space.value, useSessionUser()),
    onClick: () => {
      dialog.danger({
        title: 'Delete',
        message: 'Are you sure you want to delete this post? This is irreversible!',
        onConfirm: async () => {
          await discussion.delete.submit()
          router.replace({
            name: 'Space',
            params: {
              communityId: route.params.communityId,
              spaceId: route.params.spaceId,
            },
          })
        },
      })
    },
  },
])

useCommandPaletteCommands(
  computed(() => {
    if (props.readOnlyMode || !discussion.doc) return []

    return actions.value.map((action) => {
      const title = cleanCommandTitle(action.label)
      return {
        title,
        name: `discussion-${title.toLowerCase().replace(/\s+/g, '-')}`,
        group: 'Discussion',
        icon: action.icon,
        aliases: discussionCommandAliases(title),
        onClick: action.onClick,
        condition: action.condition,
        defaultScore: title === 'Copy link' ? 3 : 2,
      }
    })
  }),
)

function cleanCommandTitle(title: string) {
  return title.replace(/\.\.\.$/, '')
}

function discussionCommandAliases(title: string) {
  const aliases: Record<string, string[]> = {
    Edit: ['edit post', 'edit discussion'],
    Revisions: ['history', 'version history', 'edits'],
    'Copy link': ['copy url', 'share link'],
    'Mark as unread': ['unread', 'remind me'],
    Bookmark: ['save', 'save for later'],
    'Remove Bookmark': ['unsave', 'remove saved'],
    'Pin discussion': ['pin', 'keep on top'],
    'Unpin discussion': ['unpin', 'remove pin'],
    'Close discussion': ['lock discussion', 'disable comments'],
    'Re-open discussion': ['reopen', 'unlock discussion'],
    'Move to': ['move discussion', 'change space'],
    Delete: ['delete discussion', 'remove discussion'],
  }

  return aliases[title] || []
}

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
