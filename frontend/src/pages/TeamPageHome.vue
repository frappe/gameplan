<template>
  <div class="container pt-10 mx-auto pb-80">
    <div>
      <div class="flex items-center space-x-2">
        <IconPicker
          ref="teamIconPicker"
          v-model="team.doc.icon"
          @update:modelValue="(icon) => team.setValue.submit({ icon })"
        />
        <h1 class="text-6xl font-bold text-gray-900">{{ team.doc.title }}</h1>
        <Dropdown
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

      <TextEditor
        class="w-full mt-2 rounded-lg"
        :key="team.doc.name"
        :content="team.doc.description"
        placeholder="Add a description for your team"
        @change="
          (val) => {
            team.setValueDebounced.submit({ description: val })
          }
        "
      />
    </div>
    <div class="grid grid-cols-8 mt-10 gap-x-5 gap-y-12">
      <div class="col-span-8">
        <TeamPageHomeProjects :team="team" />
      </div>
      <div class="col-span-6">
        <TeamPageHomeLinks :team="team" />
      </div>
      <div class="col-span-2">
        <TeamPageHomeMembers :team="team" />
      </div>
    </div>
  </div>
</template>
<script>
import { FileUploader, Dropdown, TextEditor, Avatar } from 'frappe-ui'
import TeamPageHomeProjects from './TeamPageHomeProjects.vue'
import TeamPageHomeMembers from './TeamPageHomeMembers.vue'
import IconPicker from '@/components/IconPicker.vue'
import TeamPageHomeLinks from './TeamPageHomeLinks.vue'

export default {
  name: 'TeamPageHome',
  props: ['team'],
  components: {
    FileUploader,
    TeamPageHomeProjects,
    TeamPageHomeLinks,
    TeamPageHomeMembers,
    Dropdown,
    TextEditor,
    IconPicker,
    Avatar,
  },
  mounted() {
    if (!this.team.doc.icon) {
      this.$refs.teamIconPicker.setRandom()
    }
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
