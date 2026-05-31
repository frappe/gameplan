<template>
  <TextEditor
    ref="textEditorRef"
    class="pb-40"
    editor-class="max-w-[unset] min-h-[calc(100vh-350px)] prose-v3 overflow-auto px-2 -mx-2"
    :content="draftData.content"
    @change="(content: string) => (draftData.content = content)"
    :editable="author.name === sessionUser.name"
    placeholder="Type '/' for commands or select text to format"
  >
    <template #editor="{ editor }">
      <DiscussionHeader />

      <div class="discussion-container isolate">
        <div class="top-12 z-10 sticky">
          <div class="bg-surface-white">
            <div class="flex items-center -ml-2 pt-2 pb-1">
              <div class="hidden sm:flex transition-opacity duration-100">
                <EditorFixedMenu :editor="editor" :items="gameplanToolbar" />
              </div>
            </div>
          </div>
          <div
            class="h-4 bg-gradient-to-b from-white to-transparent dark:from-[--dark-gray-900]"
          ></div>
        </div>

        <DiscussionMetadata />
        <DiscussionEditor :editor="editor" />
      </div>
    </template>
  </TextEditor>
</template>

<script setup lang="ts">
import { useTemplateRef } from 'vue'
import { EditorFixedMenu } from 'frappe-ui/editor'
import { gameplanToolbar } from '@/components/editor/toolbars'
import TextEditor from '@/components/TextEditor.vue'
import DiscussionHeader from './DiscussionHeader.vue'
import DiscussionMetadata from './DiscussionMetadata.vue'
import DiscussionEditor from './DiscussionEditor.vue'
import { provideNewDiscussion } from './useNewDiscussion'

const textEditorRef = useTemplateRef<InstanceType<typeof TextEditor>>('textEditorRef')

const { draftData, sessionUser, author, initialize } = provideNewDiscussion(textEditorRef)

initialize()
</script>
