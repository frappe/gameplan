<template>
  <FTextEditor :mentions="users" v-bind="$attrs" ref="textEditor" />
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
      return this.$users.data.map((user) => ({
        label: user.full_name,
        value: user.name,
      }))
    },
  },
}
</script>
