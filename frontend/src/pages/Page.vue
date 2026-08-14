<template>
  <div>
    <PageHeaderMobile class="sm:hidden" :title="pageTitle">
      <template #prefix>
        <PageHeaderBackButton :to="backRoute" :label="isSpacePage ? 'Pages' : 'My Pages'" />
      </template>
      <template v-if="page.doc && canEditPage" #suffix>
        <DropdownMoreOptions align="end" :options="pageActions" />
      </template>
    </PageHeaderMobile>
    <PageHeader class="hidden sm:flex">
      <SpaceBreadcrumbs
        v-if="space"
        :spaceId="space.name"
        :items="[
          {
            label: 'Pages',
            route: {
              name: 'SpacePages',
              params: { communityId: space?.team, spaceId: space?.name },
            },
          },
          {
            label: pageTitle,
            route: {
              name: 'SpacePage',
              params: {
                communityId: space?.team,
                pageId: props.pageId,
                slug: props.slug,
                spaceId: space?.name,
              },
            },
          },
        ]"
      />
      <Breadcrumbs
        v-else
        class="h-7"
        :items="[
          { label: 'My Pages', route: { name: 'MyPages' } },
          {
            label: pageTitle,
            route: {
              name: 'Page',
              params: { pageId: props.pageId, slug: props.slug },
            },
            isPageTitle: true,
          },
        ]"
      />
      <div class="ms-2 shrink-0" v-if="page.doc && canEditPage">
        <DropdownMoreOptions align="end" :options="pageActions" />
      </div>
    </PageHeader>
    <div class="body-container">
      <div class="py-6" v-if="page.doc">
        <span class="text-sm text-ink-gray-5 sm:hidden">
          Updated {{ dayjsLocal(page.doc.modified).format('lll') }}
        </span>
        <div class="mb-3 md:px-[70px]" ref="titleField">
          <input
            class="w-full border-0 p-0 pt-4 text-5xl-semibold focus:outline-none focus:ring-0 bg-surface-base text-ink-gray-8"
            type="text"
            v-model="title"
            :readonly="!canEditPage"
            @input="autosave"
            @keydown.enter="textEditor?.editor?.commands.focus()"
            ref="titleInput"
            placeholder="Title"
          />
        </div>
        <div ref="contentField">
          <PageEditor
            editor-class="rounded-b-6 max-w-[unset] prose-v3 pb-[50vh] md:px-[70px]"
            :content="content"
            :editable="canEditPage"
            @change="
              (value) => {
                content = value
                autosave()
              }
            "
            placeholder="Start writing here..."
            ref="textEditor"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, useTemplateRef } from 'vue'
import { useRoute, useRouter, type RouteLocationRaw } from 'vue-router'
import {
  PageHeader,
  PageHeaderBackButton,
  PageHeaderMobile,
  Breadcrumbs,
  usePageMeta,
  debounce,
  dayjsLocal,
  useDoc,
  dialog,
} from 'frappe-ui'
import PageEditor from '@/components/editor/PageEditor.vue'
import { useSpace } from '@/data/spaces'
import { GPPage } from '@/types/doctypes'
import SpaceBreadcrumbs from '@/components/SpaceBreadcrumbs.vue'
import DropdownMoreOptions from '@/components/DropdownMoreOptions.vue'
import { readOnlyMode } from '@/data/readOnlyMode'
import { relativeTimestamp } from '@/utils'
import { useSessionUser } from '@/data/users'
import { canDeleteContent, canEditContent } from '@/utils/permissions'
import { useCommandPaletteCommands } from '@/components/CommandPalette/registry'
import { useOwnedRouteWrites } from '@/composables/useOwnedRouteWrites'
import { useSyncedField } from '@/utils/useSyncedField'
const props = defineProps<{
  communityId?: string
  pageId: string
  slug?: string
  spaceId?: string
}>()

const route = useRoute()
const router = useRouter()
const history = window.history

// This page also renders behind the settings overlay, where the URL belongs to /settings/*.
// Rewriting it from there would both throw (no pageId param to spread) and navigate the app
// off the settings route, closing the dialog. A page may only rewrite a URL it owns.
const runWhenOwned = useOwnedRouteWrites(() => route.name === 'SpacePage' || route.name === 'Page')

const titleInput = useTemplateRef('titleInput')
const textEditor = useTemplateRef('textEditor')
const titleField = useTemplateRef<HTMLElement>('titleField')
const contentField = useTemplateRef<HTMLElement>('contentField')

const page = useDoc<GPPage>({
  doctype: 'GP Page',
  name: () => props.pageId,
})

// Read from the document, not from the fetch response. The body renders as soon
// as `page.doc` arrives, which can be the cached copy the doc store publishes
// before the network one. Seeding only on the response left the inputs rendered
// and empty until it landed, and overwrote anything typed in that gap.
// See useSyncedField for how the two publishes are told apart.
const title = useSyncedField({
  source: () => page.doc?.title,
  identity: () => page.doc?.name,
  target: titleField,
})
const content = useSyncedField({
  source: () => page.doc?.content,
  identity: () => page.doc?.name,
  target: contentField,
})

page.onSuccess(() => {
  updateUrlSlug()
  // Only when nobody is working yet: on a slow response the body has been
  // interactive since the cached copy rendered, and pulling focus to the title
  // would yank someone out of the editor mid-sentence.
  if (!document.activeElement || document.activeElement === document.body) {
    titleInput.value?.focus()
  }
})

const isDirty = computed(() => {
  return page.doc?.title !== title.value || page.doc?.content !== content.value
})

const space = useSpace(() => page.doc?.project || props.spaceId)
const canEditPage = computed(
  () =>
    !readOnlyMode &&
    !space.value?.archived_at &&
    canEditContent(page.doc, space.value, useSessionUser()),
)

const pageTitle = computed(() => {
  return page.doc?.title || props.pageId
})

const isSpacePage = computed(() => Boolean(space.value || props.spaceId))
const backRoute = computed<RouteLocationRaw>(() => {
  const spaceId = space.value?.name || props.spaceId
  const communityId = space.value?.team || props.communityId

  if (spaceId && communityId) {
    return {
      name: 'SpacePages',
      params: { communityId, spaceId },
    }
  }

  return { name: 'MyPages' }
})

const isAutosaving = ref(false)
const MIN_AUTOSAVING_DURATION = 2000 // 2 seconds

const pageActions = computed(() => [
  {
    label: page.doc?.modified ? 'Saved ' + relativeTimestamp(page.doc.modified) : 'Saved',
    onClick: () => save(),
    loading: isAutosaving.value,
    icon: 'lucide-save',
  },
  {
    label: 'Delete',
    icon: 'lucide-trash-2',
    onClick: deletePage,
    condition: () => canEditPage.value && canDeleteContent(page.doc, space.value, useSessionUser()),
  },
])

const save = () => {
  if (!canEditPage.value) return

  isAutosaving.value = true
  const startTime = Date.now()

  page.setValue
    .submit({
      title: title.value,
      content: content.value,
    })
    .finally(() => {
      const elapsedTime = Date.now() - startTime
      const remainingTime = Math.max(0, MIN_AUTOSAVING_DURATION - elapsedTime)

      setTimeout(() => {
        isAutosaving.value = false
      }, remainingTime)
    })
}

const autosave = debounce(save, 1000)

function deletePage() {
  dialog.danger({
    title: 'Delete Page',
    message: 'Are you sure you want to delete this page?',
    onConfirm: async () => {
      await page.delete.submit()
      if (history.state.back == null) {
        router.push({ name: 'MyPages' })
      } else {
        router.back()
      }
    },
  })
}

useCommandPaletteCommands(
  computed(() => {
    if (!page.doc || !canEditPage.value) return []

    return [
      {
        title: 'Save page',
        name: 'page-save',
        group: 'Page',
        icon: 'lucide-save',
        aliases: ['save document', 'save changes'],
        onClick: save,
        defaultScore: isDirty.value ? 3 : 1,
      },
      {
        title: 'Delete page',
        name: 'page-delete',
        group: 'Page',
        icon: 'lucide-trash-2',
        aliases: ['remove page', 'delete document'],
        onClick: deletePage,
        condition: () =>
          canEditPage.value && canDeleteContent(page.doc, space.value, useSessionUser()),
        defaultScore: 1,
      },
    ]
  }),
)

const handleKeyboardShortcuts = (e: KeyboardEvent) => {
  if (canEditPage.value && e.key === 's' && (e.metaKey || e.ctrlKey)) {
    e.preventDefault()
    save()
  }
}

// Runs once per visit, when the doc resolves — so if the URL is not ours at that moment,
// the correction has to wait for it rather than be dropped for the rest of the visit.
const updateUrlSlug = () => {
  runWhenOwned(applyCanonicalSlug)
}

// Reads its state when it runs, not when it was queued, so a deferred correction can't
// stamp the slug of the page we started on onto the page the URL ended up on.
function applyCanonicalSlug() {
  const doc = page.doc
  if (!doc) return
  if (route.params.slug && route.params.slug === doc.slug) return

  router.replace({
    name: doc.project ? 'SpacePage' : 'Page',
    params: {
      ...route.params,
      communityId: doc.project ? space.value?.team : undefined,
      spaceId: doc.project,
      slug: doc.slug,
    },
    query: route.query,
  })
}

onMounted(() => {
  document.addEventListener('keydown', handleKeyboardShortcuts)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeyboardShortcuts)
})

usePageMeta(() => {
  if (!page.doc) return
  return {
    title: space.value ? `${pageTitle.value} | ${space.value.title}` : pageTitle.value,
  }
})
</script>
