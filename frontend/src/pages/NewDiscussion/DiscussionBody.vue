<template>
  <div :aria-busy="isDraftLoading">
    <div
      v-if="showDraftLoadingStatus"
      class="mb-3 flex items-center gap-2 text-sm text-ink-gray-5"
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      <LoadingIndicator class="size-3" aria-hidden="true" />
      <span>Loading draft…</span>
    </div>
    <ErrorMessage :message="errorMessage || publishError" />
    <textarea
      ref="titleTextarea"
      class="mt-1 w-full bg-transparent resize-none border-0 px-0 py-0.5 text-4xl-semibold text-ink-gray-8 placeholder-ink-gray-3 focus:ring-0"
      :value="draftData?.title"
      placeholder="Title"
      rows="1"
      wrap="soft"
      maxlength="140"
      @keydown.enter.prevent="editor.commands.focus()"
      @keydown.down.prevent="editor.commands.focus()"
      @blur="handleTitleBlur"
      :disabled="!isComposerEditable"
      @input="handleTitleInput"
    />
    <EditorContent :editor="editor" :class="editorClass" aria-label="Discussion content" />
  </div>
</template>

<script setup lang="ts">
import { nextTick, watch } from 'vue'
import { useTextareaAutosize } from '@vueuse/core'
import { ErrorMessage, LoadingIndicator } from 'frappe-ui'
import { EditorContent } from 'frappe-ui/editor'
import { useNewDiscussionContext } from './useNewDiscussion'
import type { Editor } from '@tiptap/core'

interface Props {
  editor: Editor
  // Editor-content classes (e.g. `prose-v3`) forwarded from the GPEditor
  // `#editor` slot scope — the renderless <TextEditor> applies no classes itself.
  editorClass?: unknown
}

defineProps<Props>()

// Autosize the single-visual-line title. useTextareaAutosize owns the height
// measurement; we only nudge it when the draft title changes from outside (e.g.
// a restored draft), since the content is bound via :value, not the composable's
// own input ref.
const { textarea: titleTextarea, triggerResize } = useTextareaAutosize()

const {
  errorMessage,
  publishError,
  draftData,
  isDraftLoading,
  isComposerEditable,
  showDraftLoadingStatus,
  handleTitleInput,
  handleTitleBlur,
} = useNewDiscussionContext()

watch(
  () => draftData.value?.title,
  () => nextTick(triggerResize),
  { flush: 'post' },
)

watch(
  isComposerEditable,
  async (editable) => {
    if (!editable) return
    await nextTick()
    titleTextarea.value?.focus()
  },
  { immediate: true, flush: 'post' },
)
</script>
