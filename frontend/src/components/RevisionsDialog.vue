<template>
  <Dialog v-if="!isMobile" :options="{ title, size: '5xl' }" v-model="showDialog">
    <template #body-content>
      <div v-if="orderedRevisions.length" class="grid gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
        <div class="">
          <div class="max-h-[60vh] space-y-1 -m-1 p-1 overflow-y-auto" role="listbox">
            <button
              v-for="(revision, index) in orderedRevisions"
              :key="`${revision.creation}-${index}`"
              class="w-full rounded-md px-3 py-2 text-left last:border-b-0 transition-colors focus:outline-none focus-visible:ring focus-visible:ring-outline-gray-2"
              role="option"
              :aria-selected="index === currentRevisionIndex"
              :aria-label="`Revision from ${dayjsLocal(revision.creation).format('LLL')}`"
              :class="
                index === currentRevisionIndex
                  ? 'bg-surface-gray-2 hover:bg-surface-gray-3 text-ink-gray-9'
                  : 'text-ink-gray-7 hover:bg-surface-gray-1'
              "
              type="button"
              @click="currentRevisionIndex = index"
            >
              <div class="text-sm font-medium">
                {{ dayjsLocal(revision.creation).format('LLL') }}
              </div>
              <div class="mt-0.5 text-sm text-ink-gray-5">{{ revision.owner }}</div>
            </button>
          </div>
        </div>
        <div class="min-w-0">
          <div class="mb-2 flex items-center text-base" v-if="currentRevision">
            <UserInfo :email="currentRevision.owner" v-slot="{ user }">
              <UserProfileLink class="mr-3" :user="user.name">
                <UserAvatar :user="user.name" />
              </UserProfileLink>
              <div class="space-y-0.5">
                <UserProfileLink
                  class="font-medium text-ink-gray-8 hover:text-ink-blue-4"
                  :user="user.name"
                >
                  {{ user.full_name }}
                </UserProfileLink>
                <time
                  class="block text-ink-gray-5"
                  :datetime="currentRevision.creation"
                  :title="dayjsLocal(currentRevision.creation)"
                >
                  {{ dayjsLocal(currentRevision.creation).format('LLL') }}
                </time>
              </div>
            </UserInfo>
          </div>
          <div
            v-if="currentRevision"
            v-html="htmlDiff"
            class="ProseMirror max-w-none prose prose-sm rounded-md prose-p:my-1 prose-table:table-fixed prose-th:relative prose-th:border prose-th:border-outline-gray-2 prose-th:bg-surface-gray-2 prose-th:p-2 prose-td:relative prose-td:border prose-td:border-outline-gray-2 prose-td:p-2"
          />
        </div>
      </div>
    </template>
  </Dialog>

  <BottomSheet v-else v-model="sheetVisible" @close-complete="handleSheetCloseComplete">
    <div v-if="orderedRevisions.length" class="flex flex-col">
      <div class="sticky top-0 z-10 bg-surface-white pb-2 pt-1">
        <div class="flex items-center justify-center gap-1">
          <button
            v-for="(revision, index) in orderedRevisions"
            :key="`${revision.creation}-${index}`"
            class="rounded-full"
            type="button"
            :aria-label="`Go to revision ${index + 1}`"
            :aria-selected="index === currentRevisionIndex"
            @click="currentRevisionIndex = index"
          >
            <Motion
              :initial="false"
              class="block size-2 rounded-full"
              :class="index === currentRevisionIndex ? 'bg-surface-gray-7' : 'bg-surface-gray-3'"
              :animate="{
                scale: index === currentRevisionIndex ? 1.2 : 1,
                opacity: index === currentRevisionIndex ? 1 : 0.7,
              }"
              :transition="{ type: 'spring', stiffness: 200, damping: 10 }"
            />
          </button>
        </div>
      </div>

      <div ref="previewRef" class="flex-1 overflow-y-auto px-4 pb-6">
        <div class="mb-3 flex items-center text-sm" v-if="currentRevision">
          <UserInfo :email="currentRevision.owner" v-slot="{ user }">
            <UserProfileLink class="mr-3" :user="user.name">
              <UserAvatar :user="user.name" />
            </UserProfileLink>
            <div class="space-y-0.5">
              <UserProfileLink class="font-medium text-ink-gray-8" :user="user.name">
                {{ user.full_name }}
              </UserProfileLink>
              <time
                class="block text-ink-gray-5"
                :datetime="currentRevision.creation"
                :title="dayjsLocal(currentRevision.creation)"
              >
                {{ dayjsLocal(currentRevision.creation).format('LLL') }}
              </time>
            </div>
          </UserInfo>
        </div>
        <div
          v-if="sheetContentReady && currentRevision"
          v-html="htmlDiff"
          class="ProseMirror max-w-none prose prose-sm rounded-md prose-p:my-1 prose-table:table-fixed prose-th:relative prose-th:border prose-th:border-outline-gray-2 prose-th:bg-surface-gray-2 prose-th:p-2 prose-td:relative prose-td:border prose-td:border-outline-gray-2 prose-td:p-2"
        />
        <div v-else class="h-40 rounded-md bg-surface-gray-1" aria-hidden="true" />
      </div>
    </div>
  </BottomSheet>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useMediaQuery, usePointerSwipe } from '@vueuse/core'
import { dayjsLocal, useCall } from 'frappe-ui'
import HtmlDiff from 'htmldiff-js'
import { Motion } from 'motion-v'
import BottomSheet from './BottomSheet.vue'
import UserProfileLink from './UserProfileLink.vue'

interface Revision {
  owner: string
  creation: string
  old_value: string
  new_value: string
}

interface Props {
  modelValue: boolean
  doctype: string
  name: string | number
  fieldname: string
}

const props = defineProps<Props>()
const emit = defineEmits<{ (e: 'update:modelValue', value: boolean): void }>()

const currentRevisionIndex = ref(0)
const isMobile = useMediaQuery('(max-width: 1024px)')
const showDialog = computed({
  get() {
    return props.modelValue
  },
  set(value: boolean) {
    emit('update:modelValue', value)
  },
})

const isSheetReady = computed(() => revisions.data !== undefined)
const sheetVisible = computed({
  get() {
    return showDialog.value && isSheetReady.value
  },
  set(value: boolean) {
    showDialog.value = value
  },
})
const sheetContentReady = ref(false)

const previewRef = ref<HTMLElement | null>(null)

const revisionUrl = computed(
  () => `/api/v2/document/${props.doctype}/${props.name}/method/get_revisions`,
)
const revisions = useCall<Revision[], { fieldname: string }>({
  url: revisionUrl,
  immediate: false,
})

watch(
  () => showDialog.value,
  (value) => {
    if (value) {
      currentRevisionIndex.value = 0
      revisions.submit({ fieldname: props.fieldname })
    }
  },
  { immediate: true },
)

const orderedRevisions = computed(() => {
  if (!revisions.data) {
    return []
  }
  return [...revisions.data].sort(
    (first, second) => dayjsLocal(second.creation).valueOf() - dayjsLocal(first.creation).valueOf(),
  )
})

const title = computed(() => {
  if (revisions.data) {
    if (revisions.data.length === 0) return 'No Revisions'
    if (revisions.data.length === 1) return '1 Revision'
    return `${revisions.data.length} Revisions`
  }
  return 'Loading...'
})

const currentRevision = computed(() => {
  return orderedRevisions.value[currentRevisionIndex.value] ?? null
})

const handleSheetCloseComplete = () => {
  currentRevisionIndex.value = 0
  sheetContentReady.value = false
}

watch(
  () => sheetVisible.value,
  (value) => {
    if (!value) {
      sheetContentReady.value = false
      return
    }
    sheetContentReady.value = true
  },
)

const goNextRevision = () => {
  if (!orderedRevisions.value.length) return
  currentRevisionIndex.value = Math.min(
    currentRevisionIndex.value + 1,
    orderedRevisions.value.length - 1,
  )
}

const goPreviousRevision = () => {
  if (!orderedRevisions.value.length) return
  currentRevisionIndex.value = Math.max(currentRevisionIndex.value - 1, 0)
}

const { distanceX } = usePointerSwipe(previewRef, {
  pointerTypes: ['touch'],
  onSwipeEnd(_, direction) {
    if (!isMobile.value) return
    if (Math.abs(distanceX.value) < 60) return
    if (direction === 'left') {
      goNextRevision()
      return
    }
    if (direction === 'right') {
      goPreviousRevision()
    }
  },
})

const htmlDiff = computed(() => {
  if (!currentRevision.value) {
    return null
  }

  const oldHtml = currentRevision.value.old_value
  const newHtml = currentRevision.value.new_value

  // because of commonjs and esm shenanigans
  const makeDiff = HtmlDiff.default?.execute || HtmlDiff.execute
  return makeDiff(oldHtml, newHtml)
})
</script>
<style>
ins {
  all: unset;
  background-color: theme('colors.green.100');
}
del {
  all: unset;
  background-color: theme('colors.red.100');
}
</style>
