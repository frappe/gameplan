<template>
  <div class="px-6 pt-8 overflow-auto pb-80">
    <div class="flex items-center w-full">
      <div class="flex items-center space-x-2">
        <IconPicker
          :modelValue="team.doc.icon"
          @update:modelValue="updateTeamIcon"
          :set-default="true"
        >
          <template v-slot="{ isOpen }">
            <div
              class="p-px leading-none rounded-md text-7xl focus:outline-none"
              :class="isOpen ? 'bg-gray-200' : 'hover:bg-gray-100'"
            >
              {{ team.doc.icon || '' }}
            </div>
          </template>
        </IconPicker>
        <h1 class="text-6xl font-bold text-gray-900">{{ team.doc.title }}</h1>
        <Dropdown
          placement="left"
          :options="[
            {
              label: 'Delete',
              icon: 'trash-2',
              handler: () => deleteTeam(),
            },
          ]"
          :button="{
            label: 'Options',
            appearance: 'minimal',
            icon: 'more-horizontal',
          }"
        />
      </div>
      <div class="ml-auto">
        <TeamPageHomeMembers :team="team" />
      </div>
    </div>

    <div class="mt-6 space-y-4">
      <TeamPageHomeProjects :team="team" />
      <div>
        <h2 class="mb-2 text-lg text-gray-900">Readme</h2>
        <ReadmeEditor :resource="team" fieldname="readme" />
      </div>
    </div>
  </div>
</template>
<script>
import { Dropdown } from 'frappe-ui'
import TeamPageHomeProjects from './TeamPageHomeProjects.vue'
import TeamPageHomeMembers from './TeamPageHomeMembers.vue'
import IconPicker from '@/components/IconPicker.vue'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import ReadmeEditor from '@/components/ReadmeEditor.vue'

export default {
  name: 'TeamPageHome',
  props: ['team'],
  components: {
    TeamPageHomeProjects,
    TeamPageHomeMembers,
    Dropdown,
    IconPicker,
    Breadcrumbs,
    ReadmeEditor,
  },
  methods: {
    updateTeamIcon(icon) {
      this.team.setValue.submit({ icon })
    },
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
