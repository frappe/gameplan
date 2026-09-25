<template>
  <Dialog title="Change Community" @after-leave="setCurrentTeam" v-model:open="show">
    <Combobox
      :options="teamOptions"
      v-model="selectedTeam"
      placeholder="Select a community"
      class="w-full"
      open-on-click
      autofocus
    />
    <ErrorMessage class="mt-2" :message="spaces.runDocMethod.error" />
    <template #actions>
      <Button
        class="w-full"
        variant="solid"
        :loading="spaces.runDocMethod.isLoading(spaceId, 'move_to_team')"
        @click="submit"
      >
        {{ selectedTeam ? `Move to ${selectedTeamLabel}` : 'Move to Uncategorized' }}
      </Button>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Combobox } from 'frappe-ui'
import { activeCommunities } from '@/data/communities'
import { spaces as spacesList, useSpace } from '@/data/spaces'
import { useDoctype } from 'frappe-ui'
import { GPProject } from '@/types/doctypes'

const props = defineProps<{
  spaceId: string
}>()

const show = defineModel<boolean>()
const space = useSpace(() => props.spaceId)
const spaces = useDoctype<GPProject>('GP Project')

const teamOptions = computed(() => {
  return activeCommunities.value.map((team) => ({
    label: team.title,
    value: team.name,
  }))
})

const selectedTeam = ref<string | null>(null)
const selectedTeamLabel = computed(() => {
  return teamOptions.value.find((team) => team.value === selectedTeam.value)?.label ?? ''
})

setCurrentTeam()

function setCurrentTeam() {
  let currentTeam = space.value?.team?.toString()
  if (currentTeam) {
    selectedTeam.value = currentTeam
  }
}

function submit() {
  spaces.runDocMethod
    .submit({
      method: 'move_to_team',
      name: props.spaceId,
      params: {
        team: selectedTeam?.value,
      },
    })
    .then(() => {
      // Refresh the cached spaces so denormalized fields like team_title (shown in
      // the space breadcrumb) reflect the new community.
      spacesList.reload()
      if (selectedTeam.value) {
        show.value = false
      }
    })
}
</script>
