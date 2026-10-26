<template>
  <NodeViewWrapper class="not-prose my-3" contenteditable="false">
    <a
      data-link-card
      :href="node.attrs.href"
      target="_blank"
      rel="noopener noreferrer"
      class="flex max-w-lg gap-4 rounded-6 border px-4 py-3 transition-colors hover:bg-surface-gray-1"
      :class="selected && editor.isEditable ? 'border-outline-gray-4' : 'border-outline-gray-2'"
      @click="onClick"
    >
      <div class="min-w-0 flex-1">
        <div class="truncate text-sm text-ink-gray-5">{{ siteName }}</div>
        <div class="mt-2 line-clamp-2 text-base-semibold text-ink-gray-9">
          {{ node.attrs.title || node.attrs.href }}
        </div>
        <p v-if="node.attrs.description" class="mt-2 line-clamp-2 text-p-sm text-ink-gray-6">
          {{ node.attrs.description }}
        </p>
      </div>
      <img
        v-if="image"
        :src="image"
        alt=""
        loading="lazy"
        referrerpolicy="no-referrer"
        class="size-20 shrink-0 self-center rounded-4 bg-surface-gray-2 object-cover"
        @error="imageFailed = true"
      />
    </a>
  </NodeViewWrapper>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3'

const props = defineProps(nodeViewProps)

const imageFailed = ref(false)
watch(
  () => props.node.attrs.image,
  () => (imageFailed.value = false),
)

const image = computed(() => {
  const src = props.node.attrs.image
  return !imageFailed.value && /^https?:\/\//i.test(src) ? src : ''
})

const siteName = computed(() => {
  if (props.node.attrs.siteName) return props.node.attrs.siteName
  try {
    return new URL(props.node.attrs.href).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
})

function onClick(event: MouseEvent) {
  if (props.editor.isEditable) event.preventDefault()
}
</script>
