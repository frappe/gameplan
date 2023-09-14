<template>
  <Dialog :options="{ title: 'Add Team' }" v-model="showDialog">
    <template #body-content>
      <div class="space-y-4">
        <FormControl
          label="Team Name"
          type="text"
          v-model="newTeam.title"
          placeholder="Team Name"
          @keydown.enter="createTeam($event.target.value)"
          autocomplete="off"
        />
        <FormControl
          type="select"
          label="Visibility"
          :options="[
            { label: 'Visible to everyone', value: 0 },
            { label: 'Visible to team members (Private)', value: 1 },
          ]"
          v-model="newTeam.is_private"
        />
        <ErrorMessage :message="teams.insert.error?.messages" />
      </div>
    </template>
    <template #actions>
      <Button
        variant="solid"
        class="w-full"
        @click="createTeam(teamName)"
        :loading="teams.insert.loading"
      >
        Create Team
      </Button>
    </template>
  </Dialog>
</template>
<script>
import { teams } from '@/data/teams'

export default {
  name: 'AddTeamDialog',
  props: ['show'],
  emits: ['success', 'update:show'],
  data() {
    return {
      newTeam: { title: '', is_private: 0 },
      teams,
    }
  },
  methods: {
    createTeam() {
      teams.insert.submit(this.newTeam, {
        onSuccess: (team) => {
          this.$resetData('newTeam')
          this.showDialog = false
          this.$emit('success', team)
        },
      })
    },
  },
  computed: {
    showDialog: {
      get() {
        return this.show
      },
      set(val) {
        this.$emit('update:show', val)
      },
    },
  },
}
</script>
