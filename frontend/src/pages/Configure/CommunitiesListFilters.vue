<template>
  <div class="flex items-center gap-2">
    <TextInput v-model="search" placeholder="Search communities">
      <template #prefix>
        <span class="lucide-search h-4 w-4 text-ink-gray-4" />
      </template>
    </TextInput>
    <Select :options="visibilityOptions" v-model="visibilityFilter" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Select, TextInput } from 'frappe-ui'
import { communities } from '@/data/communities'

type VisibilityFilter = 'All' | 'Public' | 'Private' | 'Archived'

const search = defineModel<string>('search', { default: '' })
const visibilityFilter = defineModel<VisibilityFilter>('visibilityFilter', { default: 'All' })

// Counts must match CommunitiesList: every community the user can read.
const visibleCommunities = computed(() => communities.data || [])
const activeCommunities = computed(() =>
  visibleCommunities.value.filter((community) => !community.archived_at),
)
const archivedCount = computed(
  () => visibleCommunities.value.length - activeCommunities.value.length,
)

const visibilityOptions = computed(() => {
  const options = [
    { label: `All (${activeCommunities.value.length})`, value: 'All' },
    {
      label: `Public (${activeCommunities.value.filter((c) => !c.is_private).length})`,
      value: 'Public',
    },
    {
      label: `Private (${activeCommunities.value.filter((c) => c.is_private).length})`,
      value: 'Private',
    },
  ]
  // Only offer the archived scope when there's something archived to show.
  if (archivedCount.value) {
    options.push({ label: `Archived (${archivedCount.value})`, value: 'Archived' })
  }
  return options
})
</script>
