<template>
  <div class="flex items-center">
    <template v-for="(item, i) in items" :key="item.label">
      <router-link
        class="flex items-center rounded px-0.5 py-1 text-lg font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
        :class="[
          i == items.length - 1
            ? 'text-gray-900'
            : 'text-gray-600 hover:text-gray-700',
        ]"
        :to="item.route"
      >
        <span class="mr-2 text-2xl leading-none" v-if="item.icon">
          {{ item.icon }}
        </span>
        <span>
          {{ item.label }}
        </span>
      </router-link>
      <span v-if="i != items.length - 1" class="mx-0.5 text-base text-gray-500">
        /
      </span>
    </template>
  </div>
</template>
<script>
export default {
  name: 'PageBreadcrumbs',
  props: {
    items: {
      type: Array,
      required: true,
    },
  },
}
</script>
