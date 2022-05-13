<template>
  <nav class="flex items-center" aria-label="Breadcrumbs">
    <template v-for="(breadcrumb, i) in breadcrumbList" :key="breadcrumb.title">
      <router-link
        v-if="breadcrumb.route"
        :to="breadcrumb.route"
        class="flex items-center space-x-1.5 text-lg text-gray-900 hover:bg-gray-100 px-1.5 py-1 -mx-1.5 -my-1 rounded-md"
      >
        <span class="text-xl" v-if="breadcrumb.icon">
          {{ breadcrumb.icon }}
        </span>
        <span>
          {{ breadcrumb.title }}
        </span>
      </router-link>
      <FeatherIcon
        v-if="i < breadcrumbList.length - 1"
        name="chevron-right"
        class="w-4 mx-1"
      />
      <div
        class="flex items-center space-x-1.5 text-lg text-gray-600"
        v-if="!breadcrumb.route"
      >
        <span class="text-xl" v-if="breadcrumb.icon">
          {{ breadcrumb.icon }}
        </span>
        <span>
          {{ breadcrumb.title }}
        </span>
      </div>
    </template>
  </nav>
</template>
<script>
export default {
  name: 'Breadcrumbs',
  props: ['breadcrumbs'],
  computed: {
    breadcrumbList() {
      return this.breadcrumbs.filter(Boolean)
    },
  },
}
</script>
