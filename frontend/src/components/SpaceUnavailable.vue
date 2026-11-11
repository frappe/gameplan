<template>
  <div v-if="spacesStatus === 'failed'">
    <PageHeader>
      <Breadcrumbs :items="[communityCrumb]" />
    </PageHeader>
    <div class="body-container py-8">
      <LoadError
        :message="errorText(spaces.error, 'Could not load spaces.')"
        :retrying="spaces.loading"
        @retry="spaces.reload()"
      />
    </div>
  </div>
  <NotFound
    v-else-if="spacesStatus === 'ready'"
    title="Space not found"
    description="It may have been deleted, or you no longer have access to it."
  >
    <template #breadcrumbs>
      <Breadcrumbs :items="[communityCrumb, { label: 'Not found' }]" />
    </template>
  </NotFound>
</template>

<script setup lang="ts">
// Stands in for a space page whose space is not in the spaces list: either the list
// failed to load (retryable) or it loaded without this space (not found).
import { computed } from 'vue'
import { Breadcrumbs, PageHeader } from 'frappe-ui'
import NotFound from '@/pages/NotFound.vue'
import LoadError from './LoadError.vue'
import { spaces, spacesStatus } from '@/data/spaces'
import { useCommunity } from '@/data/communities'
import { errorText } from '@/utils'

const props = defineProps<{ communityId: string }>()

const community = useCommunity(() => props.communityId)
const communityCrumb = computed(() => ({
  label: community.value?.title || 'Community',
  route: { name: 'Discussions', params: { communityId: props.communityId } },
}))
</script>
