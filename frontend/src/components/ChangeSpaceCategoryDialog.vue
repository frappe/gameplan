<template>
  <Dialog
    :options="{
      title: 'Change Category',
    }"
    @after-leave="
      () => {
        selectedTeam = null
        projects.runDocMethod.reset()
      }
    "
    v-model="show"
  >
    <template #body-content>
      <Autocomplete :options="teamOptions" v-model="selectedTeam" placeholder="Select a team">
        <template #item-prefix="{ option }">
          <span class="mr-2">{{ option.icon }}</span>
        </template>
      </Autocomplete>
      <ErrorMessage
        class="mt-2"
        :message="
          projects.runDocMethod.params?.method === 'move_to_team' && projects.runDocMethod.error
        "
      />
    </template>
    <template #actions>
      <Button
        class="w-full"
        variant="solid"
        :loading="
          projects.runDocMethod.params?.method === 'move_to_team' && projects.runDocMethod.loading
        "
        @click="submit"
      >
        {{ selectedTeam ? `Move to ${selectedTeam.label}` : 'Move' }}
      </Button>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Autocomplete } from 'frappe-ui'
import { projects, getProject } from '@/data/projects'
import { activeTeams } from '@/data/teams'

const props = defineProps<{
  spaceId: string | number
}>()

const show = defineModel<boolean>()
const space = computed(() => getProject(props.spaceId))

const teamOptions = computed(() => {
  return [
    {
      label: 'No category',
      value: '',
    },
    ...activeTeams.value.map((team) => ({
      label: team.title,
      value: team.name,
    })),
  ]
})

const selectedTeam = ref(
  teamOptions.value.find(
    (team) => team.value?.toString() === (space.value?.team?.toString() || ''),
  ),
)

function submit() {
  projects.runDocMethod.submit(
    {
      method: 'move_to_team',
      name: props.spaceId,
      team: selectedTeam.value?.value,
    },
    {
      validate() {
        if (!selectedTeam.value) {
          return 'Please select a team'
        }
      },
      onSuccess() {
        if (selectedTeam.value) {
          show.value = false
        }
      },
    },
  )
}
</script>
