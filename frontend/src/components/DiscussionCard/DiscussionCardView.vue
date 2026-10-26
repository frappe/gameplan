<template>
  <NodeViewWrapper class="not-prose my-3" contenteditable="false">
    <a
      v-if="preview !== null"
      data-discussion-card
      :href="node.attrs.href"
      class="block max-w-lg rounded-6 border px-4 py-3 transition-colors hover:bg-surface-gray-1"
      :class="selected && editor.isEditable ? 'border-outline-gray-4' : 'border-outline-gray-2'"
      @click="onClick"
    >
      <div class="truncate text-sm text-ink-gray-5">
        <template v-if="preview">
          {{ spacePath(preview.project) }} on
          {{ dayjsLocal(preview.creation).format('MMM D, YYYY') }}
        </template>
        <template v-else>&nbsp;</template>
      </div>
      <div class="mt-2 line-clamp-2 text-base-semibold text-ink-gray-9">
        {{ preview?.title || node.attrs.title }}
      </div>
      <p v-if="preview?.snippet" class="mt-2 line-clamp-2 text-p-sm text-ink-gray-6">
        {{ preview.snippet }}
      </p>
    </a>
    <a v-else :href="node.attrs.href" class="text-base text-ink-gray-9 underline" @click="onClick">
      {{ node.attrs.title || node.attrs.href }}
    </a>
  </NodeViewWrapper>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3'
import { dayjsLocal } from 'frappe-ui'
import { loadDiscussionPreview, type DiscussionPreview } from '@/data/discussionPreviews'
import { spacePath } from '@/utils/discussionLinks'

const props = defineProps(nodeViewProps)

const preview = ref<DiscussionPreview | null | undefined>(undefined)

watch(
  () => props.node.attrs.discussion,
  async (name) => {
    preview.value = undefined
    if (!name) {
      preview.value = null
      return
    }
    const result = await loadDiscussionPreview(name)
    if (props.node.attrs.discussion === name) preview.value = result
  },
  { immediate: true },
)

function onClick(event: MouseEvent) {
  if (props.editor.isEditable) event.preventDefault()
}
</script>
