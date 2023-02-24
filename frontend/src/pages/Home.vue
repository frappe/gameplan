<template>
  <Feed :feedType="feedType" />
</template>
<script>
import Feed from './Feed.vue'

export default {
  name: 'Home',
  props: ['feedType'],
  components: {
    Feed,
  },
}
</script>
