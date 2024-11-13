<template>
  <router-link custom :to="link.route" v-slot="{ href, isActive, isExactActive, navigate }">
    <a
      ref="elementRef"
      v-bind="$attrs"
      :href="href"
      @click="navigate"
      :class="[
        linkClasses(isActive, isExactActive),
        typeof link.class == 'function' ? link.class($route, link) : link.class,
        $attrs.class,
      ]"
    >
      <slot :link="link">
        {{ link.name }}
      </slot>
    </a>
  </router-link>
</template>
<script>
export default {
  name: 'Link',
  inheritAttrs: false,
  props: ['link', 'active', 'exact-active', 'inactive'],
  expose: ['getRef'],
  methods: {
    linkClasses(isActive, isExactActive) {
      if (isExactActive) {
        return this.exactActive || this.active
      }
      if (this.link.isActive || (isActive && !this.exactActive)) {
        return this.active
      }
      return this.inactive
    },
    getRef() {
      return this.$refs.elementRef
    },
  },
}
</script>
