<template>
  <div>
    <ErrorMessage :message="errorMessage || draftDoc?.publish.error" />
    <textarea
      class="mt-1 w-full bg-transparent resize-none border-0 px-0 py-0.5 text-2xl text-ink-gray-8 font-semibold placeholder-ink-gray-3 focus:ring-0"
      :value="draftData.title"
      placeholder="Title"
      rows="1"
      wrap="soft"
      maxlength="140"
      v-focus
      @keydown.enter.prevent="editor.commands.focus()"
      @keydown.down.prevent="editor.commands.focus()"
      @focus="handleTextareaFocus"
      @blur="handleTextareaBlur"
      :disabled="sessionUser.name != author.name"
      @input="handleTitleInput"
    />
    <TextEditorContent :editor="editor" />
  </div>
</template>

<script setup lang="ts">
import { ErrorMessage, TextEditorContent } from 'frappe-ui'
import { vFocus } from '@/directives'
import { useNewDiscussionContext } from './useNewDiscussion'
import type { TextEditorInstance } from './types'

interface Props {
  editor: TextEditorInstance['editor']
}

defineProps<Props>()

const {
  errorMessage,
  draftDoc,
  draftData,
  sessionUser,
  author,
  handleTextareaFocus,
  handleTextareaBlur,
  handleTitleInput,
} = useNewDiscussionContext()
</script>
