<template>
  <FTextEditor :mentions="users" v-bind="$attrs" ref="textEditor">
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
export default {
  name: 'TextEditor',
  inheritAttrs: false,
  components: { FTextEditor },
  expose: ['editor'],
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
  },
}
</script>
