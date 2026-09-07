<template>
  <NodeViewWrapper class="gp-collapsible my-2 first:mt-0 last:mb-0" :data-open="isOpen">
    <button
      type="button"
      contenteditable="false"
      class="gp-collapsible-toggle text-ink-gray-5 hover:bg-surface-gray-2 active:bg-surface-gray-3 aria-expanded:bg-surface-gray-3 h-6 w-6 rounded-3"
      :aria-expanded="isOpen"
      :aria-label="isOpen ? 'Collapse section' : 'Expand section'"
      @click="toggle"
    >
      <!--
        A solid triangle, the disclosure convention GitHub's <details> and
        Notion's toggle both use. The same-colour stroke is what rounds the
        three points: `stroke-linejoin: round` only softens corners that a
        stroke actually draws, so a fill-only triangle stays sharp. The path is
        drawn inset to leave room for it, keeping the outer size honest.
        Arbitrary px because the spacing scale is integers only, so `size-3.25`
        would silently not compile.
      -->
      <svg
        viewBox="0 0 24 24"
        fill="currentColor"
        stroke="currentColor"
        stroke-width="2.5"
        stroke-linejoin="round"
        class="size-[13px]"
      >
        <path d="M9.5 6.5 L18 12 L9.5 17.5 Z" />
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
/*
 * 1.75rem puts the title on the same x as bullet-list and task-list text
 * (measured in the editor: both land ~28px past the block's left edge), so a
 * section reads as one more item in the same column rather than a block that
 * starts somewhere new.
 */
.gp-collapsible {
  position: relative;
  padding-left: 1.75rem;
}

/*
 * A 24px rounded square matching `Button size="xs"` (h-6 w-6 rounded-3), sized
 * by utility classes on the element itself. An expanded section holds the
 * button in frappe-ui's on-state fill: the toolbar uses
 * `aria-pressed:bg-surface-gray-3`, and this drives the same shade off
 * `aria-expanded`, which is the correct attribute for a disclosure control.
 * Centred in the 28px gutter, which puts its midpoint on the task-list
 * checkbox's midpoint. It is
 * `contenteditable="false"` so ProseMirror treats it as a widget rather than
 * text; `user-select: none` keeps it out of a drag-selection of the title.
 */
.gp-collapsible-toggle {
  position: absolute;
  left: 0;
  /* Centre on the title's first line, whatever its line-height. `1lh` is the
   * same unit frappe-ui's task list uses; the plain `top: 0` above it is the
   * fallback where the unit is unsupported. */
  top: 0;
  top: calc((1lh - 1.5rem) / 2);
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
}

/*
 * Only the chevron turns. Rotating the button would spin its hover square with
 * it, and the `>` keeps an outer section's open state off a nested section's
 * chevron.
 */
.gp-collapsible-toggle > svg {
  transition: transform 150ms ease;
}

.gp-collapsible[data-open='true'] > .gp-collapsible-toggle > svg {
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
