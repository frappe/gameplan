<template>
  <div class="py-6">
    <h1 class="mb-3 text-2xl font-semibold">Search</h1>
    <AppSearch />
  </div>
</template>
<script>
import { Input } from 'frappe-ui'
import AppSearch from '@/components/AppSearch.vue'
export default {
  name: 'Search',
  components: { Input, AppSearch },
}
</script>
