<template>
  <div class="pt-8 pb-20">
    <div class="flex w-full items-center">
      <div class="flex items-center space-x-2">
        <IconPicker
          :modelValue="team.doc.icon"
          @update:modelValue="updateTeamIcon"
          :set-default="true"
        >
          <template v-slot="{ isOpen }">
            <div
              class="rounded-md p-px text-7xl leading-none focus:outline-none"
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
        <TeamHomeMembers :team="team" />
      </div>
    </div>
    <Tabs :tabs="tabs" />
    <router-view :team="team" />
  </div>
</template>
<script>
import { Dropdown } from 'frappe-ui'
import TeamHomeMembers from './TeamHomeMembers.vue'
import IconPicker from '@/components/IconPicker.vue'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import ReadmeEditor from '@/components/ReadmeEditor.vue'
import Tabs from '@/components/Tabs.vue'

export default {
  name: 'TeamHome',
  props: ['team'],
  components: {
    TeamHomeMembers,
    Dropdown,
    IconPicker,
    Breadcrumbs,
    ReadmeEditor,
    Tabs,
  },
  computed: {
    tabs() {
      return [
        {
          name: 'Overview',
          route: {
            name: 'TeamOverview',
          },
          isActive: this.$route.name === 'TeamOverview',
        },
        {
          name: 'Projects',
          route: {
            name: 'TeamProjects',
          },
          isActive: this.$route.name === 'TeamProjects',
        },
      ]
    },
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
              return this.team.delete.submit(null, {
                onSuccess: () => {
                  this.$router.push('/')
                  close()
                },
              })
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
