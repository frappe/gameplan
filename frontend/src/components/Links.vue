<template>
  <Link
    v-for="link in links"
    :key="link.name"
    :class="$attrs.class"
    v-bind="{ link, active, exactActive, inactive }"
  />
</template>
<script>
import Link from './Link.vue'
export default {
  name: 'Links',
  props: ['links', 'active', 'exact-active', 'inactive'],
  inheritAttrs: false,
  components: {
    Link,
  },
}
</script>
