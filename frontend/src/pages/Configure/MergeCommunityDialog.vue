<template>
  <Dialog title="Merge community" @after-leave="selectedCommunity = null" v-model:open="show">
    <p class="mb-4 text-p-base text-ink-gray-7">
      This will move all spaces and members from
      <span class="whitespace-nowrap font-semibold">{{ community.title }}</span>
      into the selected community. The old community will be archived and content links will use
      each item's current space.
    </p>
    <Combobox
      :options="communityOptions"
      v-model="selectedCommunity"
      placeholder="Select a community"
      class="w-full"
      open-on-click
      autofocus
    />
    <ErrorMessage class="mt-2" :message="teams.runDocMethod.error" />
    <template #actions>
      <Button
        class="w-full"
        variant="solid"
        :loading="teams.runDocMethod.isLoading(community.name, 'merge_into_team')"
        @click="submit"
      >
        {{ selectedCommunity ? `Merge into ${selectedCommunityLabel}` : 'Merge' }}
      </Button>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Combobox, useDoctype } from 'frappe-ui'
import { communities, type Community } from '@/data/communities'
import { spaces } from '@/data/spaces'
import { useSessionUser } from '@/data/users'
import type { GPTeam } from '@/types/doctypes'
import { getManageableCommunities } from '@/utils/permissions'

const props = defineProps<{
  community: Community
}>()
const emit = defineEmits<{
  (event: 'merged', communityId: string): void
}>()

const show = defineModel<boolean>()
const teams = useDoctype<GPTeam>('GP Team')
const sessionUser = useSessionUser()
const selectedCommunity = ref<string | null>(null)

const communityOptions = computed(() => {
  return getManageableCommunities(communities.data || [], sessionUser)
    .filter((community) => !community.archived_at && community.name !== props.community.name)
    .map((community) => ({
      label: community.title,
      value: community.name,
    }))
})
const selectedCommunityLabel = computed(() => {
  return (
    communityOptions.value.find((community) => community.value === selectedCommunity.value)
      ?.label ?? ''
  )
})

function submit() {
  teams.runDocMethod
    .submit({
      method: 'merge_into_team',
      name: props.community.name,
      params: {
        team: selectedCommunity.value,
      },
      validate() {
        if (!selectedCommunity.value) {
          return 'Select a community to merge into'
        }
      },
    })
    .then(async () => {
      const targetCommunity = selectedCommunity.value
      await Promise.all([communities.reload(), spaces.reload()])
      show.value = false
      if (targetCommunity) {
        emit('merged', targetCommunity)
      }
    })
}
</script>
