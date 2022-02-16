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
          :button="{ appearance: 'minimal', icon: 'more-horizontal' }"
        ></Dropdown>
      </div>

      <TeamPageHomeMembers :team="team" />

      <TipTap
        class="w-full px-3 py-2 mt-4 -mx-3 prose-sm prose max-w-[unset] rounded-lg focus-within:bg-gray-50"
        :key="team.name"
        :content="team.description"
        placeholder="Add a description for your team"
        @update="
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
import TipTap from '@/components/TipTap.vue'
import { FileUploader, Dropdown } from 'frappe-ui'
import TeamPageHomeProjects from './TeamPageHomeProjects.vue'
import TeamPageHomeMembers from './TeamPageHomeMembers.vue'
import TeamPageHomeCover from './TeamPageHomeCover.vue'

export default {
  name: 'TeamPageHome',
  props: ['team'],
  components: {
    TipTap,
    FileUploader,
    TeamPageHomeProjects,
    TeamPageHomeMembers,
    TeamPageHomeCover,
    Dropdown,
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
          this.$refetchResource(['team', this.team.name])
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
