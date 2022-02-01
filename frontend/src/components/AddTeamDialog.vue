<template>
  <NewDialog :options="{ title: 'Add Team' }" v-model="showDialog">
    <template #dialog-content>
      <Input
        label="Team Name"
        type="text"
        v-model="teamName"
        placeholder="Team Name"
      />
      <ErrorMessage class="mt-2" :error="$resources.createTeam.error" />
    </template>

    <template #dialog-actions>
      <Button
        type="primary"
        @click="
          $resources.createTeam.submit({
            name: teamName,
          })
        "
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
      teamType: '',
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
    createTeam: {
      method: 'teams.api.create_team',
      onSuccess(team) {
        this.$emit('success', team)
      },
    },
  },
}
</script>
