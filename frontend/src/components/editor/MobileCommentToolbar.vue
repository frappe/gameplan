<script setup lang="ts">
import { computed } from 'vue'
import type { Editor } from 'frappe-ui/editor'
import CommentToolbarContent from './CommentToolbarContent.vue'
import { useKeyboardInset } from '@/composables/useKeyboardInset'

// Mobile-only formatting toolbar rendered as a rounded pill that floats directly
// above the on-screen keyboard. Teleported to <body> and fixed-positioned so it
// escapes the composer's scroll/overflow and tracks the keyboard via the
// VisualViewport inset.
const props = defineProps<{
  editor: Editor
  toolbarExpanded: boolean
  // Shown only while the editor is focused (i.e. the keyboard is up for it).
  visible: boolean
}>()

const emit = defineEmits<{
  'update:toolbarExpanded': [value: boolean]
}>()

const { inset } = useKeyboardInset()

const style = computed(() => ({
  // Sit on top of the keyboard; when no keyboard is detected fall back to the
  // safe-area inset so the pill clears the home indicator.
  bottom: inset.value > 0 ? `${inset.value}px` : 'env(safe-area-inset-bottom, 0px)',
}))
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="translate-y-2 opacity-0"
      enter-to-class="translate-y-0 opacity-100"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="translate-y-0 opacity-100"
      leave-to-class="translate-y-2 opacity-0"
    >
      <div
        v-if="visible"
        class="fixed inset-x-0 z-40 flex justify-center px-2 pb-2"
        :style="style"
        role="toolbar"
        aria-label="Comment formatting"
        aria-orientation="horizontal"
        @mousedown.prevent
      >
        <div
          class="flex max-w-full items-center gap-1 overflow-x-auto rounded-full border border-outline-gray-2 bg-surface-white px-1.5 py-1 shadow-lg"
        >
          <CommentToolbarContent
            :editor="editor"
            :toolbar-expanded="toolbarExpanded"
            @update:toolbar-expanded="emit('update:toolbarExpanded', $event)"
          />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
