<template>
  <TextEditor
    ref="textEditorRef"
    class="pb-40"
    editor-class="max-w-[unset] min-h-[calc(100vh-350px)] prose-sm overflow-auto"
    :content="draftData.content"
    @change="(content: string) => (draftData.content = content)"
    :editable="author.name === sessionUser.name"
    placeholder="Type '/' for commands or select text to format"
  >
    <template #editor="{ editor }">
      <DiscussionHeader />

      <div class="mx-auto max-w-3xl px-4 xl:px-0 isolate">
        <div class="top-12 z-10" :class="[showFixedMenu ? 'sticky' : ' static']">
          <div class="bg-surface-white">
            <div class="flex items-center -ml-2 pt-2 pb-1">
              <div
                :class="[
                  showFixedMenu ? 'opacity-100' : 'opacity-0',
                  'hidden sm:flex transition-opacity duration-100',
                ]"
              >
                <TextEditorFixedMenu :buttons="true" />
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
import { TextEditorFixedMenu } from 'frappe-ui'
import TextEditor from '@/components/TextEditor.vue'
import DiscussionHeader from './DiscussionHeader.vue'
import DiscussionMetadata from './DiscussionMetadata.vue'
import DiscussionEditor from './DiscussionEditor.vue'
import { provideNewDiscussion } from './useNewDiscussion'

const textEditorRef = useTemplateRef<InstanceType<typeof TextEditor>>('textEditorRef')

const { draftData, sessionUser, author, showFixedMenu, initialize } =
  provideNewDiscussion(textEditorRef)

initialize()
</script>
