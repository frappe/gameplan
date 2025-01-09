<template>
  <div>
    <header
      class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-5 py-2.5"
    >
      <Breadcrumbs class="h-7" :items="breadcrumbs">
        <template #prefix="{ item }">
          <span class="mr-2 flex rounded-sm text-2xl leading-none" v-if="item.icon">
            {{ item.icon }}
          </span>
        </template>
        <template #suffix="{ item }">
          <div v-if="item.isPageTitle && isAutosaving" class="text-base text-ink-gray-5 ml-2">
            Autosaving...
          </div>
        </template>
      </Breadcrumbs>
      <div class="flex items-center space-x-2">
        <span class="hidden text-sm text-ink-gray-5 sm:block" v-if="page.doc">
          Last updated {{ $dayjs(page.doc.modified).format('LLL') }}
        </span>
      </div>
    </header>
    <div class="mx-auto w-full max-w-4xl px-5">
      <div class="py-6" v-if="page.doc">
        <span class="text-sm text-ink-gray-5 sm:hidden">
          Last updated {{ $dayjs(page.doc.modified).format('LLL') }}
        </span>
        <div class="mb-3 md:px-[70px]">
          <input
            class="w-full border-0 p-0 pt-4 text-3xl font-semibold focus:outline-none focus:ring-0 bg-surface-white text-ink-gray-9"
            type="text"
            v-model="title"
            @input="autosave"
            @keydown.enter="textEditor?.editor?.commands.focus()"
            ref="titleInput"
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
import { Breadcrumbs, TextEditor, usePageMeta, debounce } from 'frappe-ui'
import { useDoc } from 'frappe-ui/src/data-fetching'
import { useSpace } from '@/data/spaces'
import { GPPage } from '@/types/doctypes'
import KeyboardShortcut from '@/components/KeyboardShortcut.vue'

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

  if (!space.value) return []
  return [
    {
      label: 'Spaces',
      route: { name: 'Spaces' },
    },
    {
      label: space.value?.title,
      route: {
        name: 'Space',
        params: { spaceId: space.value.name },
      },
    },
    {
      label: 'Pages',
      route: {
        name: 'SpacePages',
        params: { spaceId: space.value.name },
      },
    },
    {
      label: pageTitle.value,
      route: {
        name: 'SpacePage',
        params: { pageId: props.pageId, slug: props.slug, spaceId: space.value.name },
      },
    },
  ]
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
