<template>
  <Dialog :options="{title: 'Add Team'}" v-model="showDialog">
    <Input
      label="Team Name"
      type="text"
      v-model="teamName"
      placeholder="Team Name"
    />
    <ErrorMessage class="mt-2" :error="$resources.createTeam.error" />

    <template #actions>
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
  </Dialog>
</template>
<script>
import NewDialog from "frappe-ui/src/components/NewDialog.vue"

export default {
  name: 'AddTeamDialog',
  emits: ['success'],
  data() {
    return {
      teamName: '',
      teamType: '',
      showDialog: true,
    }
  },
  components: {
    NewDialog,
  },
  methods: {},
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
