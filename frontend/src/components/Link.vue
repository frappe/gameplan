<template>
  <router-link
    custom
    :to="link.route"
    v-slot="{ href, isActive, isExactActive, navigate }"
  >
    <a
      v-bind="$attrs"
      :href="href"
      @click="navigate"
      :class="[
        linkClasses(isActive, isExactActive),
        link.class ? link.class($route, link) : null,
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
  methods: {
    linkClasses(isActive, isExactActive) {
      if (isExactActive) {
        return this.exactActive || this.active
      }
      if (isActive && !this.exactActive) {
        return this.active
      }
      return this.inactive
    },
  },
}
</script>
