<template>
  <div :aria-busy="isDraftLoading">
    <LoadError
      v-if="draftLoadFailed"
      class="mt-4"
      message="Could not load this draft."
      @retry="retryDraftLoad"
    />
    <template v-else>
      <div v-if="showDraftLoadingStatus" class="mb-3" role="status" aria-live="polite">
        <LoadingText text="Loading draft…" />
      </div>
      <p
        v-else-if="author && author.name !== sessionUser.name"
        class="mb-3 text-sm text-ink-gray-5"
      >
        {{ author.full_name }}'s draft. Only they can edit or publish it.
      </p>
      <!-- One slot above the title for failures. A failed publish wins over a failed
           autosave: publishing flushes first, so its message already covers the save. -->
      <Alert
        v-if="submitError"
        class="mb-3"
        theme="red"
        :title="submitError.message"
        :primary-action="
          submitError.retry
            ? { label: 'Retry', loading: publishing, onClick: submitError.retry }
            : undefined
        "
      />
      <Alert
        v-else-if="saveFailed"
        class="mb-3"
        theme="amber"
        title="Couldn't save your draft"
        description="Your changes are still on this page. Gameplan tries again as you edit."
        :primary-action="{ label: 'Retry', onClick: retrySave }"
      />
      <ErrorMessage v-else :message="errorMessage || scheduleWarning" />
      <textarea
        ref="titleTextarea"
        class="mt-1 w-full bg-transparent resize-none border-0 px-0 py-0.5 text-3xl-semibold text-ink-gray-8 placeholder-ink-gray-3 focus:ring-0"
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
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, watch } from 'vue'
import { useTextareaAutosize } from '@vueuse/core'
import { Alert, ErrorMessage, LoadingText } from 'frappe-ui'
import LoadError from '@/components/LoadError.vue'
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
  submitError,
  publishing,
  draftData,
  isDraftLoading,
  draftLoadFailed,
  retryDraftLoad,
  saveFailed,
  retrySave,
  isComposerEditable,
  showDraftLoadingStatus,
  author,
  sessionUser,
  handleTitleInput,
  handleTitleBlur,
  scheduledAt,
} = useNewDiscussionContext()

const scheduleWarning = computed(() =>
  scheduledAt.value && !draftData.value?.title?.trim()
    ? 'Add a title to publish on scheduled time'
    : '',
)

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
