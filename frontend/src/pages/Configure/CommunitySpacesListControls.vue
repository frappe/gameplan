<template>
  <div>
    <div class="flex items-center justify-between gap-3">
      <div class="flex min-w-0 flex-1 items-center gap-2 sm:flex-none">
        <TextInput class="min-w-0 flex-1 sm:flex-none" v-model="search" placeholder="Search spaces">
          <template #prefix>
            <span class="lucide-search h-4 w-4 text-ink-gray-4" />
          </template>
        </TextInput>
        <Select :options="visibilityOptions" v-model="visibilityFilter" />
      </div>
      <slot name="action" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Select, TextInput } from 'frappe-ui'
import { useCommunitySpaceData } from './useCommunitySpaceData'
import { VISIBILITY_TIERS, visibilityTier, type Visibility } from '@/utils/visibility'

type VisibilityFilter = 'All' | Visibility | 'Archived'

const props = defineProps<{ communityId: string }>()
const search = defineModel<string>('search', { default: '' })
const visibilityFilter = defineModel<VisibilityFilter>('visibilityFilter', { default: 'All' })

const { communitySpaces } = useCommunitySpaceData(() => props.communityId)

const activeSpaces = computed(() => communitySpaces.value.filter((space) => !space.archived_at))
const archivedCount = computed(() => communitySpaces.value.length - activeSpaces.value.length)

const visibilityOptions = computed(() => {
  const options = [
    { label: `All (${activeSpaces.value.length})`, value: 'All' },
    ...VISIBILITY_TIERS.map((tier) => ({
      label: `${tier} (${activeSpaces.value.filter((s) => visibilityTier(s.visibility) === tier).length})`,
      value: tier,
    })),
  ]
  if (archivedCount.value) {
    options.push({ label: `Archived (${archivedCount.value})`, value: 'Archived' })
  }
  return options
})
</script>
