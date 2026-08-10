<template>
  <NodeViewWrapper class="gp-collapsible my-2 first:mt-0 last:mb-0" :data-open="isOpen">
    <button
      type="button"
      contenteditable="false"
      class="gp-collapsible-toggle text-ink-gray-5 hover:bg-surface-gray-2 rounded"
      :aria-expanded="isOpen"
      :aria-label="isOpen ? 'Collapse section' : 'Expand section'"
      @click="toggle"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        class="h-4 w-4"
      >
        <path d="m9 18 6-6-6-6" />
      </svg>
    </button>
    <NodeViewContent class="gp-collapsible-body" />
  </NodeViewWrapper>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { NodeViewContent, NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3'

const props = defineProps(nodeViewProps)

/**
 * Display state is always local, so a reader can collapse a section without the
 * document changing. Only an editable editor writes the choice back to the
 * `open` attribute, where it becomes part of the saved HTML and the default the
 * next reader sees. `editor.isEditable` is a plain property (not reactive), so
 * it is read at click time rather than tracked.
 */
const isOpen = ref<boolean>(props.node.attrs.open !== false)

watch(
  () => props.node.attrs.open,
  (open) => {
    isOpen.value = open !== false
  },
)

function toggle() {
  isOpen.value = !isOpen.value
  if (props.editor.isEditable) {
    props.updateAttributes({ open: isOpen.value })
  }
}
</script>

<style scoped>
.gp-collapsible {
  position: relative;
  padding-left: 1.5rem;
}

/*
 * The toggle sits in the gutter, aligned to the first line of the title. It is
 * `contenteditable="false"` so ProseMirror treats it as a widget rather than
 * text; `user-select: none` keeps it out of a drag-selection of the title.
 */
.gp-collapsible-toggle {
  position: absolute;
  left: 0;
  top: 0.125rem;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 1.25rem;
  width: 1.25rem;
  user-select: none;
  transition: transform 150ms ease;
}

.gp-collapsible[data-open='true'] > .gp-collapsible-toggle {
  transform: rotate(90deg);
}

/*
 * Descendant selectors, not direct-child ones: @tiptap/vue-3 injects its own
 * `div[data-node-view-content-vue]` between the content element and the node's
 * children, so `>` matches nothing. A nested collapsible picks up the same
 * rules, which is what we want — and when an outer section is closed its whole
 * subtree is hidden with it.
 */
.gp-collapsible :deep(summary) {
  display: block;
  font-weight: 500;
  cursor: text;
}

/* Suppress the native disclosure triangle; the gutter button replaces it. */
.gp-collapsible :deep(summary)::marker,
.gp-collapsible :deep(summary)::-webkit-details-marker {
  display: none;
  content: '';
}

.gp-collapsible[data-open='false'] :deep([data-type='collapsible-content']) {
  display: none;
}

.gp-collapsible :deep([data-type='collapsible-content']) {
  margin-top: 0.25rem;
}
</style>
