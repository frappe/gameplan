<template>
  <div class="pb-20">
    <div class="sticky top-0 z-10 border-b bg-white px-5 pt-3">
      <div class="flex w-full items-center">
        <div class="flex items-center space-x-2">
          <IconPicker
            class="flex"
            :modelValue="team.doc.icon"
            @update:modelValue="updateTeamIcon"
            :set-default="true"
          >
            <template v-slot="{ isOpen }">
              <div
                class="rounded-md p-px text-5xl leading-none focus:outline-none"
                :class="isOpen ? 'bg-gray-200' : 'hover:bg-gray-100'"
              >
                {{ team.doc.icon || '' }}
              </div>
            </template>
          </IconPicker>
          <h1 class="text-2xl font-medium text-gray-900">
            {{ team.doc.title }}
          </h1>
          <Badge v-if="team.doc.archived_at">Archived</Badge>
          <Tooltip
            v-if="team.doc.is_private"
            text="This team is only visible to team members"
          >
            <FeatherIcon name="lock" class="h-4 w-4" />
          </Tooltip>
          <Dropdown
            v-if="!team.doc.archived_at"
            placement="left"
            :options="[
              {
                label: 'Archive',
                icon: 'trash-2',
                handler: () => archiveTeam(),
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
      <Tabs :tabs="tabs" class="border-none" />
    </div>
    <router-view class="mx-auto max-w-4xl px-5" :team="team" />
  </div>
</template>
<script>
import { Dropdown, Badge, Tooltip, FeatherIcon } from 'frappe-ui'
import TeamHomeMembers from './TeamHomeMembers.vue'
import IconPicker from '@/components/IconPicker.vue'
import Tabs from '@/components/Tabs.vue'

export default {
  name: 'Team',
  props: ['team'],
  components: {
    TeamHomeMembers,
    Dropdown,
    IconPicker,
    Tabs,
    Tooltip,
    Badge,
    FeatherIcon,
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
        {
          name: 'Discussions',
          route: {
            name: 'TeamDiscussions',
          },
          isActive: this.$route.name === 'TeamDiscussions',
        },
      ]
    },
  },
  methods: {
    updateTeamIcon(icon) {
      this.team.setValue.submit({ icon })
    },
    archiveTeam() {
      this.$dialog({
        title: 'Archive Team',
        message: 'Are you sure you want to archive the team?',
        actions: [
          {
            label: 'Archive',
            appearance: 'primary',
            handler: ({ close }) => {
              return this.team.archive.submit(null, {
                onSuccess: () => {
                  this.$router.replace({ name: 'Home' })
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
