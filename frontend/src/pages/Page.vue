<template>
  <div>
    <header
      class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-5 py-2.5"
    >
      <SpaceBreadcrumbs
        v-if="spaceId"
        :spaceId="spaceId"
        :items="[
          {
            label: 'Pages',
            route: {
              name: 'SpacePages',
              params: { spaceId: space?.name },
            },
          },
          {
            label: pageTitle,
            route: {
              name: 'SpacePage',
              params: { pageId: props.pageId, slug: props.slug, spaceId: space?.name },
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
      <div class="ml-2 shrink-0" v-if="page.doc">
        <div v-if="isAutosaving" class="flex items-center space-x-1 text-base text-ink-gray-5 ml-2">
          <LoadingIndicator class="size-3.5" />
          <span> Autosaving... </span>
        </div>
        <span v-else class="hidden text-sm text-ink-gray-5 sm:block">
          Updated {{ dayjsLocal(page.doc.modified).format('lll') }}
        </span>
      </div>
    </header>
    <div class="mx-auto w-full max-w-4xl px-5">
      <div class="py-6" v-if="page.doc">
        <span class="text-sm text-ink-gray-5 sm:hidden">
          Updated {{ dayjsLocal(page.doc.modified).format('lll') }}
        </span>
        <div class="mb-3 md:px-[70px]">
          <input
            class="w-full border-0 p-0 pt-4 text-3xl font-semibold focus:outline-none focus:ring-0 bg-surface-white text-ink-gray-8"
            type="text"
            v-model="title"
            @input="autosave"
            @keydown.enter="textEditor?.editor?.commands.focus()"
            ref="titleInput"
            placeholder="Title"
          />
        </div>
        <TextEditor
          editor-class="rounded-b-lg max-w-[unset] prose-sm pb-[50vh] md:px-[70px]"
          :content="content"
          @change="
            (value) => {
              content = value
              autosave()
            }
          "
          placeholder="Start writing here..."
          :bubbleMenu="true"
          ref="textEditor"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, useTemplateRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Breadcrumbs, TextEditor, usePageMeta, debounce, dayjsLocal } from 'frappe-ui'
import { useDoc } from 'frappe-ui/src/data-fetching'
import { useSpace } from '@/data/spaces'
import { GPPage } from '@/types/doctypes'
import SpaceBreadcrumbs from '@/components/SpaceBreadcrumbs.vue'
import { LoadingIndicator } from 'frappe-ui'

const props = defineProps<{
  pageId: string
  slug: string
  spaceId?: string
}>()

const route = useRoute()
const router = useRouter()

const titleInput = useTemplateRef('titleInput')
const textEditor = useTemplateRef('textEditor')

const title = ref('')
const content = ref('')

const page = useDoc<GPPage>({
  doctype: 'GP Page',
  name: () => props.pageId,
})

page.onSuccess((doc) => {
  title.value = doc.title || ''
  content.value = doc.content || ''
  updateUrlSlug()
  titleInput.value?.focus()
})

const isDirty = computed(() => {
  return page.doc?.title !== title.value || page.doc?.content !== content.value
})

const space = useSpace(() => page.doc?.project)

const pageTitle = computed(() => {
  return page.doc?.title || props.pageId
})

const breadcrumbs = computed(() => {
  if (!page.doc) return []
  if (!page.doc.project) {
    return [
      { label: 'My Pages', route: { name: 'MyPages' } },
      {
        label: pageTitle.value,
        route: {
          name: 'Page',
          params: { pageId: props.pageId, slug: props.slug },
        },
        isPageTitle: true,
      },
    ]
  }
})

const isAutosaving = ref(false)
const MIN_AUTOSAVING_DURATION = 2000 // 2 seconds

const save = () => {
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

const handleKeyboardShortcuts = (e: KeyboardEvent) => {
  if (e.key === 's' && (e.metaKey || e.ctrlKey)) {
    e.preventDefault()
    save()
  }
}

const updateUrlSlug = () => {
  if (!route.params.slug || route.params.slug !== page.doc?.slug) {
    router.replace({
      name: page.doc?.project ? 'SpacePage' : 'Page',
      params: {
        ...route.params,
        spaceId: page.doc?.project,
        slug: page.doc?.slug,
      },
      query: route.query,
    })
  }
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
