<template>
  <DiscussionEditor
    editor-class="max-w-[unset] min-h-[calc(100vh-200px)] pb-40 prose-v3 overflow-auto px-2 -mx-2"
    :content="draftData.content"
    @change="(content: string) => (draftData.content = content)"
    :editable="isComposerEditable"
    placeholder="Type '/' for commands or select text to format"
  >
    <template #editor="{ editor, editorClass }">
      <DiscussionHeader />
      <PageHeaderBase
        class="hidden h-10 items-center border-b bg-surface-base px-3 sm:flex sm:px-5"
      >
        <div
          class="w-full overflow-x-auto transition-opacity"
          :class="{ 'opacity-50': isDraftLoading }"
          :inert="isDraftLoading"
          :aria-disabled="isDraftLoading"
        >
          <EditorFixedMenu :editor="editor" :items="gameplanToolbar" />
        </div>
      </PageHeaderBase>

      <div class="discussion-container isolate pt-4">
        <DiscussionSpaceSelector size="md" class="mb-2 w-full sm:hidden" />
        <DiscussionBody :editor="editor" :editor-class="editorClass" />
      </div>

      <div
        v-if="author.name === sessionUser.name"
        :inert="isDraftLoading"
        :aria-disabled="isDraftLoading"
        class="fixed inset-x-0 bottom-14 z-20 border-t bg-surface-base px-2 pt-1 pb-2 shadow-[0_-1px_3px_rgba(15,23,42,0.06)] sm:hidden standalone:bottom-[4.5rem]"
        :class="{ 'opacity-50': isDraftLoading }"
      >
        <div
          class="relative overflow-x-auto before:pointer-events-none before:absolute before:inset-y-0 before:left-0 before:z-10 before:w-5 before:bg-gradient-to-r before:from-surface-base before:to-transparent after:pointer-events-none after:absolute after:inset-y-0 after:right-0 after:z-10 after:w-5 after:bg-gradient-to-l after:from-surface-base after:to-transparent"
        >
          <EditorFixedMenu
            :editor="editor"
            :items="mobileDiscussionToolbar"
            class="mobile-editor-toolbar min-w-max justify-center"
          />
        </div>
      </div>
    </template>
  </DiscussionEditor>
</template>

<script setup lang="ts">
import { PageHeaderBase } from 'frappe-ui'
import { EditorFixedMenu } from 'frappe-ui/editor'
import { gameplanToolbar, mobileDiscussionToolbar } from '@/components/editor/toolbars'
import DiscussionEditor from '@/components/editor/DiscussionEditor.vue'
import DiscussionHeader from './DiscussionHeader.vue'
import DiscussionSpaceSelector from './DiscussionSpaceSelector.vue'
import DiscussionBody from './DiscussionBody.vue'
import { provideNewDiscussion } from './useNewDiscussion'

const { draftData, sessionUser, author, isDraftLoading, isComposerEditable, initialize } =
  provideNewDiscussion()

initialize()
</script>

<style scoped>
.mobile-editor-toolbar :deep(button) {
  height: 2.25rem;
  width: 2.25rem;
}

.mobile-editor-toolbar :deep(button .size-4) {
  height: 1.125rem;
  width: 1.125rem;
}
</style>
