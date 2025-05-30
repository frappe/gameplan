<template>
  <Dialog
    :options="{
      title: 'Change Category',
    }"
    @after-leave="() => (selectedTeam = null)"
    v-model="show"
  >
    <template #body-content>
      <Combobox :options="teamOptions" v-model="selectedTeam" placeholder="Select a team" v-focus />
      <ErrorMessage class="mt-2" :message="spaces.runDocMethod.error" />
    </template>
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
import { activeTeams } from '@/data/teams'
import { useSpace } from '@/data/spaces'
import { useDoctype } from 'frappe-ui/src/data-fetching'
import { GPProject } from '@/types/doctypes'
import { vFocus } from '@/directives'

const props = defineProps<{
  spaceId: string
}>()

const show = defineModel<boolean>()
const space = useSpace(() => props.spaceId)
const spaces = useDoctype<GPProject>('GP Project')

const teamOptions = computed(() => {
  return activeTeams.value.map((team) => ({
    label: team.title,
    value: team.name,
  }))
})

const selectedTeam = ref<string | null>(space.value?.team?.toString() ?? null)
const selectedTeamLabel = computed(() => {
  return teamOptions.value.find((team) => team.value === selectedTeam.value)?.label ?? ''
})

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
      if (selectedTeam.value) {
        show.value = false
      }
    })
}
</script>
