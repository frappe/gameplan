<template>
  <Dialog
    :options="{
      title: 'Change Category',
    }"
    @after-leave="() => (selectedTeam = null)"
    v-model="show"
  >
    <template #body-content>
      <Autocomplete :options="teamOptions" v-model="selectedTeam" placeholder="Select a team">
        <template #item-prefix="{ option }">
          <span class="mr-2">{{ option.icon }}</span>
        </template>
      </Autocomplete>
      <ErrorMessage class="mt-2" :message="spaces.runDocMethod.error" />
    </template>
    <template #actions>
      <Button
        class="w-full"
        variant="solid"
        :loading="spaces.runDocMethod.isLoading(spaceId, 'move_to_team')"
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
import { activeTeams } from '@/data/teams'
import { useSpace } from '@/data/spaces'
import { useDoctype } from 'frappe-ui/src/data-fetching'
import { GPProject } from '@/types/doctypes'

const props = defineProps<{
  spaceId: string
}>()

const show = defineModel<boolean>()
const space = useSpace(() => props.spaceId)
const spaces = useDoctype<GPProject>('GP Project')

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

const selectedTeam = ref<{ label: string; value: string } | null>(
  teamOptions.value.find(
    (team) => team.value?.toString() === (space.value?.team?.toString() || ''),
  ) ?? null,
)

function submit() {
  spaces.runDocMethod
    .submit({
      method: 'move_to_team',
      name: props.spaceId,
      validate() {
        if (!selectedTeam.value) {
          return 'Please select a team'
        }
      },
      params: {
        team: selectedTeam.value?.value,
      },
    })
    .then(() => {
      if (selectedTeam.value) {
        show.value = false
      }
    })
}
</script>
