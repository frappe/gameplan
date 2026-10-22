<template>
  <div class="flex items-center gap-2">
    <TextInput
      class="min-w-0 flex-1 sm:flex-none"
      v-model="search"
      placeholder="Search communities"
    >
      <template #prefix>
        <span class="lucide-search h-4 w-4 text-ink-gray-4" />
      </template>
    </TextInput>
    <Select class="shrink-0" :options="visibilityOptions" v-model="visibilityFilter" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Select, TextInput } from 'frappe-ui'
import { communities } from '@/data/communities'
import { visibilityFilterOptions, type VisibilityFilter } from '@/utils/visibility'

const search = defineModel<string>('search', { default: '' })
const visibilityFilter = defineModel<VisibilityFilter>('visibilityFilter', { default: 'All' })

const visibilityOptions = computed(() => visibilityFilterOptions(communities.data || []))
</script>
