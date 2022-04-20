<template>
  <!-- <TeamPageHomeCover
    class="relative z-10"
    :key="team.doc.name"
    :team="team"
    @change="
      (values) => {
        team.setValue.submit(values)
      }
    "
  /> -->

  <div class="container pt-10 mx-auto pb-80">
    <div>
      <div class="flex items-center">
        <h1 class="text-6xl font-bold">{{ team.doc.title }}</h1>
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
        :key="team.doc.name"
        :content="team.doc.description"
        :showBubbleMenu="true"
        placeholder="Add a description for your team"
        @change="
          (val) => {
            team.setValueDebounced.submit({ description: val })
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
            loading: this.team.delete.loading,
            handler: ({ close }) => {
              let teams = this.$getResource('teams')
              this.team.delete.submit().then(() => teams.reload())
              // optimistic update
              teams.setData((data) =>
                data.filter((team) => team.name !== this.team.doc.name)
              )
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
