<template>
  <FTextEditor
    ref="textEditor"
    :mentions="users"
    :tags="tags"
    :upload-function="uploadFunction"
    :extensions="extensions"
    v-bind="$attrs"
  >
    <template #editor="props">
      <slot name="editor" v-bind="props" />
    </template>
    <template #top>
      <slot name="top" />
    </template>
    <template #bottom>
      <slot name="bottom" />
    </template>
  </FTextEditor>
</template>

<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import { TextEditor as FTextEditor } from 'frappe-ui'
import { useFileUpload } from 'frappe-ui/src/utils/useFileUpload'
import FloatingQuoteButton from './RichQuoteExtension/floating-quote-button'
import RichQuoteNodeExtension from './RichQuoteExtension/rich-quote-node-extension'
import { activeUsers } from '@/data/users'
import { tags as _tags } from '@/data/tags'

const textEditor = useTemplateRef<InstanceType<FTextEditor>>('textEditor')

const emit = defineEmits(['rich-quote', 'rich-quote-click'])

const uploadFunction = (file: File) => {
  let fileUpload = useFileUpload()
  return fileUpload.upload(file).then((fileDoc) => {
    return { src: fileDoc.file_url }
  })
}

const editor = computed(() => {
  return textEditor.value?.editor
})

const users = computed(() => {
  return activeUsers.value.map((user) => ({
    label: user.full_name.trimEnd(),
    value: user.name,
  }))
})

const tags = computed(() => {
  return (
    _tags.data?.map((tag) => ({
      id: tag.name,
      label: tag.label,
    })) || []
  )
})

const extensions = computed(() => {
  return [
    FloatingQuoteButton.configure({
      onClick: (html) => {
        emit('rich-quote', html)
      },
    }),
    RichQuoteNodeExtension.configure({
      onClick: ({ quoteId, author, content }) => {
        emit('rich-quote-click', { quoteId, author, content })
      },
    }),
  ]
})

defineExpose({ editor })
</script>
