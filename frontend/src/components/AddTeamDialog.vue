<template>
  <NewDialog :options="{ title: 'Add Team' }" v-model="showDialog">
    <template #dialog-content>
      <Input
        label="Team Name"
        type="text"
        v-model="teamName"
        placeholder="Team Name"
        @keydown.enter="
          (e) => $resources.createTeam.submit({ name: e.target.value })
        "
      />
      <ErrorMessage
        class="mt-2"
        :message="$resources.createTeam.error?.message"
      />
    </template>

    <template #dialog-actions>
      <Button
        type="primary"
        @click="$resources.createTeam.submit()"
        :loading="$resources.createTeam.loading"
      >
        Create Team
      </Button>
    </template>
  </NewDialog>
</template>
<script>
import { NewDialog } from 'frappe-ui'

export default {
  name: 'AddTeamDialog',
  props: ['show'],
  emits: ['success', 'update:show'],
  data() {
    return {
      teamName: '',
    }
  },
  components: {
    NewDialog,
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
  resources: {
    createTeam() {
      return {
        method: 'teams.api.create_team',
        params: {
          name: this.teamName,
        },
        validate(params) {
          if (!params?.name) {
            return 'Team Name is required'
          }
        },
        onSuccess(team) {
          this.teamName = ''
          this.$emit('success', team)
        },
      }
    },
  },
}
</script>
