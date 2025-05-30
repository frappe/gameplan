<template>
  <div class="flex min-h-0 flex-col">
    <h2 class="text-xl font-semibold">Archived Teams</h2>
    <div v-if="archivedTeams.length" class="mt-6 divide-y overflow-y-auto pb-16">
      <div
        v-for="team in archivedTeams"
        :key="team.id"
        class="flex items-center justify-between py-2"
      >
        <div class="flex items-center space-x-2">
          <span class="flex-shrink-0">
            <span class="h-6 w-6 rounded-full">{{ team.icon }}</span>
          </span>
          <span class="text-base font-medium text-ink-gray-8">
            {{ team.title }}
          </span>
        </div>
        <Button
          :loading="teams.runDocMethod.loading && teams.runDocMethod.params?.dn === team.name"
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
              },
            )
          "
        >
          Unarchive
        </Button>
      </div>
      <ErrorMessage class="pt-2" :message="teams.runDocMethod.error" />
    </div>
    <div v-else class="text-sm text-ink-gray-5">No archived teams</div>
  </div>
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
