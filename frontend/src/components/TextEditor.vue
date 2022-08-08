<template>
  <FTextEditor :mentions="users" v-bind="$attrs" />
</template>
<script>
import { TextEditor as FTextEditor } from 'frappe-ui'
export default {
  name: 'TextEditor',
  inheritAttrs: false,
  components: { FTextEditor },
  computed: {
    users() {
      return this.$users.data.map((user) => ({
        label: user.full_name,
        value: user.name,
      }))
    },
  },
}
</script>
