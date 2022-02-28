<template>
  <TeamPageHomeCover
    class="relative z-10"
    :key="team.name"
    :team="team"
    @change="
      (values) => {
        $resources.updateTeam.submit(values)
      }
    "
  />

  <div class="container mx-auto pb-80">
    <div class="mt-10">
      <div class="flex items-center">
        <h1 class="text-6xl font-bold">{{ team.title }}</h1>
        <Dropdown
          class="ml-2"
          placement="left"
          :options="[
            {
              label: 'Delete',
              icon: 'trash-2',
              handler: () => this.deleteTeam(),
            },
          ]"
          :button="{
            label: 'Options',
            appearance: 'minimal',
            icon: 'more-horizontal',
          }"
        />
      </div>

      <TeamPageHomeMembers :team="team" />

      <TextEditor
        class="w-full px-3 py-2 -mx-3 mt-4 prose-sm prose max-w-[unset] rounded-lg focus-within:bg-gray-50"
        :key="team.name"
        :content="team.description"
        :showBubbleMenu="true"
        placeholder="Add a description for your team"
        @change="
          (val) => {
            $resources.updateTeam.submit({ description: val })
          }
        "
      />
    </div>
    <TeamPageHomeProjects class="mt-10" :team="team" />
  </div>
</template>
<script>
import { FileUploader, Dropdown, TextEditor } from 'frappe-ui'
import TeamPageHomeProjects from './TeamPageHomeProjects.vue'
import TeamPageHomeMembers from './TeamPageHomeMembers.vue'
import TeamPageHomeCover from './TeamPageHomeCover.vue'

export default {
  name: 'TeamPageHome',
  props: ['team'],
  components: {
    FileUploader,
    TeamPageHomeProjects,
    TeamPageHomeMembers,
    TeamPageHomeCover,
    Dropdown,
    TextEditor,
  },
  resources: {
    updateTeam() {
      return {
        method: 'frappe.client.set_value',
        makeParams(values) {
          return {
            doctype: 'Team',
            name: this.team.name,
            fieldname: values,
          }
        },
        debounce: 500,
        onSuccess() {
          this.$refetchResource(['Team', this.team.name])
        },
      }
    },
    deleteTeam() {
      return {
        method: 'frappe.client.delete',
        params: {
          doctype: 'Team',
          name: this.team.name,
        },
        onSuccess() {
          this.$refetchResource('teams')
        },
      }
    },
  },
  methods: {
    deleteTeam() {
      this.$dialog({
        title: 'Delete Team',
        message: 'Are you sure you want to delete the team?',
        icon: {
          name: 'trash-2',
          appearance: 'danger',
        },
        actions: [
          {
            label: 'Delete Team',
            appearance: 'danger',
            loading: this.$resources.deleteTeam.loading,
            handler: ({ close }) => {
              this.$resources.deleteTeam.submit()
              this.$router.push('/')
              close()
            },
          },
          {
            label: 'Cancel',
            handler: 'cancel',
          },
        ],
      })
    },
  },
}
</script>
