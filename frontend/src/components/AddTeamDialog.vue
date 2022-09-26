<template>
  <Dialog :options="{ title: 'Add Team' }" v-model="showDialog">
    <template #body-content>
      <Input
        label="Team Name"
        type="text"
        v-model="teamName"
        placeholder="Team Name"
        @keydown.enter="createTeam($event.target.value)"
      />
      <ErrorMessage class="mt-2" :message="teams.insert.error?.messages" />
    </template>
    <template #actions>
      <Button
        appearance="primary"
        @click="createTeam(teamName)"
        :loading="teams.insert.loading"
      >
        Create Team
      </Button>
    </template>
  </Dialog>
</template>
<script>
import { Dialog } from 'frappe-ui'
import { teams } from '@/data/teams'

export default {
  name: 'AddTeamDialog',
  props: ['show'],
  emits: ['success', 'update:show'],
  data() {
    return {
      teamName: '',
      teams,
    }
  },
  components: {
    Dialog,
  },
  methods: {
    createTeam(teamName) {
      teams.insert.submit(
        { title: teamName },
        {
          onSuccess: (team) => {
            this.teamName = ''
            this.showDialog = false
            this.$emit('success', team)
          },
        }
      )
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
