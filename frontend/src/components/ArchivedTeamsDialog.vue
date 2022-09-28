<template>
  <Dialog :options="{ title: 'Archived Teams' }" v-model="show">
    <template #body-content>
      <div v-if="archivedTeams.length" class="divide-y">
        <div
          v-for="team in archivedTeams"
          :key="team.id"
          class="flex items-center justify-between py-2"
        >
          <div class="flex items-center space-x-2">
            <span class="flex-shrink-0">
              <span class="h-6 w-6 rounded-full">{{ team.icon }}</span>
            </span>
            <span class="text-base font-medium text-gray-900">
              {{ team.title }}
            </span>
          </div>
          <Button
            :loading="
              teams.runDocMethod.loading &&
              teams.runDocMethod.params?.dn === team.name
            "
            @click="
              teams.runDocMethod.submit(
                {
                  name: team.name,
                  method: 'unarchive',
                },
                {
                  onSuccess: () => {
                    teams.reload()
                    $router.push({
                      name: 'Team',
                      params: { teamId: team.name },
                    })
                    show = false
                  },
                }
              )
            "
          >
            Unarchive
          </Button>
        </div>
        <ErrorMessage class="pt-2" :message="teams.runDocMethod.error" />
      </div>

      <div v-else class="text-sm text-gray-600">No archived teams</div>
    </template>
  </Dialog>
</template>
<script>
import { teams } from '@/data/teams'

export default {
  name: 'ArchivedTeamsDialog',
  props: ['modelValue'],
  emits: ['update:modelValue'],
  data() {
    return {
      teams,
    }
  },
  computed: {
    archivedTeams() {
      return teams.data.filter((team) => team.archived_at)
    },
    show: {
      get() {
        return this.modelValue
      },
      set(value) {
        this.$emit('update:modelValue', value)
      },
    },
  },
}
</script>
