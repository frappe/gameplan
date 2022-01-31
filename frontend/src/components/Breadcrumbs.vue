<template>
  <nav class="flex" aria-label="Breadcrumb">
    <ol role="list" class="flex items-center space-x-4">
      <li v-for="(page, i) in pages" :key="page.name">
        <div class="flex items-center">
          <svg
            v-if="i > 0"
            class="flex-shrink-0 w-5 h-5 mr-4 text-gray-300"
            xmlns="http://www.w3.org/2000/svg"
            fill="currentColor"
            viewBox="0 0 20 20"
            aria-hidden="true"
          >
            <path d="M5.555 17.776l8-16 .894.448-8 16-.894-.448z" />
          </svg>
          <Link
            class="text-sm font-medium hover:text-gray-700"
            :class="page.current ? 'text-gray-700' : 'text-gray-500'"
            :link="{ name: page.label, route: page.route }"
            :aria-current="page.current ? 'page' : undefined"
          />
        </div>
      </li>
    </ol>
  </nav>
</template>
<script>
import Link from './Link.vue'
export default {
  name: 'Breadcrumbs',
  props: ['pages'],
  components: { Link },
}
</script>
