<template>
  <FTextEditor
    :mentions="users"
    :upload-function="uploadFunction"
    v-bind="$attrs"
    :extensions="extensions"
    ref="textEditor"
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
<script>
import { TextEditor as FTextEditor } from 'frappe-ui'
import { useFileUpload } from 'frappe-ui/src/utils/useFileUpload'
import FloatingQuoteButton from './RichQuoteExtension/floating-quote-button'
import RichQuoteNodeExtension from './RichQuoteExtension/rich-quote-node-extension'

export default {
  name: 'TextEditor',
  inheritAttrs: false,
  components: { FTextEditor },
  expose: ['editor'],
  methods: {
    uploadFunction(file) {
      let fileUpload = useFileUpload()
      return fileUpload.upload(file).then((fileDoc) => {
        return { src: fileDoc.file_url }
      })
    },
  },
  computed: {
    editor() {
      return this.$refs.textEditor.editor
    },
    users() {
      return this.$users.data
        .filter((user) => user.enabled)
        .map((user) => ({
          label: user.full_name.trimEnd(),
          value: user.name,
        }))
    },
    extensions() {
      return [
        FloatingQuoteButton.configure({
          onClick: (html) => {
            this.$emit('rich-quote', html)
          },
        }),
        RichQuoteNodeExtension.configure({
          onClick: ({ quoteId, author, content }) => {
            this.$emit('rich-quote-click', { quoteId, author, content })
          },
        }),
      ]
    },
  },
}
</script>
