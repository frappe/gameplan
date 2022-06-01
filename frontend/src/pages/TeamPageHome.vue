<template>
  <header
    class="sticky top-0 z-10 flex items-center h-12 px-4 py-3 bg-white border-b"
  >
    <Breadcrumbs
      :breadcrumbs="[
        {
          title: team.doc.title,
          icon: team.doc.icon,
        },
      ]"
    />
  </header>
  <div class="px-6 pt-8 overflow-auto pb-80">
    <div>
      <div class="flex items-center space-x-2">
        <IconPicker
          v-model="team.doc.icon"
          @update:modelValue="(icon) => team.setValue.submit({ icon })"
          :set-default="true"
        >
          <template v-slot="{ open }">
            <div
              class="p-px leading-none rounded-md text-7xl focus:outline-none"
              :class="open ? 'bg-gray-200' : 'hover:bg-gray-100'"
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
    </div>
    <div class="grid grid-cols-8 gap-6 mt-6">
      <div class="col-span-6 space-y-6">
        <TeamPageHomeProjects :team="team" />
        <ReadmeEditor :resource="team" fieldname="readme" />
      </div>
      <div class="col-span-2">
        <TeamPageHomeMembers :team="team" />
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
