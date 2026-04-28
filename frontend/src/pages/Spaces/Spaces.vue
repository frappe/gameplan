<template>
  <PageHeader>
    <Breadcrumbs class="h-7" :items="[{ label: 'Spaces', route: { name: 'Spaces' } }]" />
    <Button
      icon-left="lucide-plus"
      @click="
        () => {
          categoryForNewSpace = ''
          newSpaceDialog = true
        }
      "
    >
      Add new
    </Button>
  </PageHeader>
  <NewSpaceDialog v-model="newSpaceDialog" :category="categoryForNewSpace" />
  <div class="body-container">
    <div class="mt-6 mb-3 flex items-center justify-between gap-2.5">
      <TextInput
        ref="searchInputRef"
        v-model="query"
        :debounce="150"
        :placeholder="$platform == 'mac' ? 'Search (⌘+F)' : 'Search (Ctrl+F)'"
        class="w-full"
        v-focus="!!!$route.query.teamId"
      >
        <template #prefix>
          <span class="lucide-search size-4 text-ink-gray-5" />
        </template>
      </TextInput>
      <TabButtons
        :buttons="[{ label: 'Public' }, { label: 'Private' }, { label: 'Archived' }]"
        v-model="currentTab"
      />
    </div>
    <div class="p-3" v-if="!hasAnySpaces">
      <EmptyStateBox>
        <div class="text-ink-gray-5 text-base">No spaces</div>
      </EmptyStateBox>
    </div>
    <div class="mb-10" v-if="filteredPinnedSpaces.length > 0">
      <div class="flex items-center text-base text-ink-gray-8 py-2">
        <span class="lucide-pin inline h-4 w-4 mr-2" />
        <span> Pinned </span>
      </div>
      <div class="grid sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        <PinnedSpaceCard v-for="d in filteredPinnedSpaces" :key="d.name" :spaceId="d.project" />
      </div>
    </div>
    <RecycleScroller
      ref="scroller"
      key-field="name"
      :items="groupedSpaces"
      size-field="height"
      @scroll-end="onScrollEnd"
    >
      <template #default="{ item }">
        <SpaceCardGroup
          :ref="(el) => setGroupRefs(el, item.name)"
          :group="item"
          class="scroll-mt-12"
          @new-space="
            (categoryName) => {
              categoryForNewSpace = categoryName
              newSpaceDialog = true
            }
          "
        />
      </template>
    </RecycleScroller>
  </div>
</template>
<script setup lang="ts">
import { ref, nextTick, computed, onMounted, onUnmounted, useTemplateRef } from 'vue'
import { RecycleScroller } from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'
import { useRoute } from 'vue-router'
import { Breadcrumbs, TabButtons, Button, TextInput } from 'frappe-ui'
import { useWindowSize } from '@vueuse/core'
import NewSpaceDialog from '@/components/NewSpaceDialog.vue'
import PageHeader from '@/components/PageHeader.vue'
import EmptyStateBox from '@/components/EmptyStateBox.vue'
import SpaceCardGroup from './SpaceCardGroup.vue'
import PinnedSpaceCard from './PinnedSpaceCard.vue'
import { useGroupedSpaces } from '@/data/groupedSpaces'
import { vFocus } from '@/directives'
import { pinnedSpaces } from '@/data/pinnedSpaces'
import { useSpace } from '@/data/spaces'

const currentTab = ref('Public')
const categoryForNewSpace = ref('')
const query = ref('')
const route = useRoute()
const scroller = ref(null)
const searchInputRef = useTemplateRef<InstanceType<typeof TextInput>>('searchInputRef')

const filteredPinnedSpaces = computed(() => {
  if (currentTab.value !== 'Public' || !pinnedSpaces.data) return []

  return pinnedSpaces.data.filter((d) => {
    const space = useSpace(d.project).value
    if (!space) return false
    if (!query.value) return true
    return space.title.toLowerCase().includes(query.value.toLowerCase())
  })
})

const groupedSpaces = computed(() => {
  let _groupedSpaces = useGroupedSpaces({
    filterFn: (space) =>
      Boolean(
        {
          Public: !space.archived_at,
          Private: space.is_private,
          Archived: space.archived_at,
        }[currentTab.value],
      ) && (query.value ? space.title.toLowerCase().includes(query.value.toLowerCase()) : true),
  })

  let out = []

  let categoryHeight = 44
  let cardHeight = 66.95
  let gap = 12
  let gapBetweenGroups = 48

  for (const group of _groupedSpaces.value) {
    let rows = Math.ceil(group.spaces.length / columns.value)
    let gapHeight = (rows - 1) * gap
    let groupHeight = categoryHeight + gapHeight + rows * cardHeight + gapBetweenGroups
    out.push({
      ...group,
      height: groupHeight,
    })
  }
  return out
})

const hasAnySpaces = computed(() => {
  return filteredPinnedSpaces.value.length > 0 || groupedSpaces.value.length > 0
})

const newSpaceDialog = ref(false)
const groupRefs = ref<Record<string, InstanceType<typeof SpaceCardGroup>>>({})

async function onScrollEnd() {
  if (route.query.teamId) {
    await nextTick()
    setTimeout(() => {
      scrollToCategory(route.query.teamId as string)
    }, 100)
  }
}

function scrollToCategory(categoryId: string) {
  const groupElement = groupRefs.value[categoryId]
  if (groupElement?.$el) {
    groupElement.$el.scrollIntoView({ block: 'start' })
  }
}

function setGroupRefs(el: any, name: string) {
  if (el) {
    groupRefs.value[name] = el
  }
}

const columns = computed(() => {
  const { width } = useWindowSize()
  if (width.value < 768) return 1
  if (width.value < 1024) return 2
  if (width.value < 1280) return 3
  return 4
})

function handleKeyDown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
    const inputEl = searchInputRef.value?.el
    if (inputEl && document.activeElement !== inputEl) {
      e.preventDefault()
      inputEl.focus()
    }
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})
</script>
