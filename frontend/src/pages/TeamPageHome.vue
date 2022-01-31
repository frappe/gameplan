<template>
  <TeamPageHomeCover
    :team="team"
    @change="
      (imageUrl) => {
        team.cover_image = imageUrl
        $resources.updateTeam.submit()
      }
    "
  />

  <div class="mx-auto pb-80 max-w-main-content">
    <div class="w-3/5 mt-10">
      <div class="flex items-center justify-between">
        <h1 class="text-6xl font-bold">{{ team.title }}</h1>
      </div>

      <TipTap
        :key="team.name"
        :content="team.description"
        @update="
          (val) => {
            team.description = val
            $resources.updateTeam.submit()
          }
        "
      />
    </div>
    <TeamPageHomeProjects class="w-3/5 mt-10" :team="team" />
    <TeamPageHomeMembers class="w-3/5 mt-10" :team="team" />
  </div>
</template>
<script>
import TipTap from '@/components/TipTap.vue'
import { FileUploader, NewDialog } from 'frappe-ui'
import TeamPageHomeProjects from './TeamPageHomeProjects.vue'
import TeamPageHomeMembers from './TeamPageHomeMembers.vue'
import TeamPageHomeCover from './TeamPageHomeCover.vue'

export default {
  name: 'TeamPageHome',
  props: ['team'],
  components: {
    TipTap,
    FileUploader,
    NewDialog,
    TeamPageHomeProjects,
    TeamPageHomeMembers,
    TeamPageHomeCover,
  },
  resources: {
    updateTeam() {
      return {
        method: 'frappe.client.set_value',
        params: {
          doctype: 'Team',
          name: this.team.name,
          fieldname: {
            title: this.team.title,
            description: this.team.description,
            cover_image: this.team.cover_image,
          },
        },
        debounce: 500,
        onSuccess() {
          this.$refetchResource(['team', this.team.name])
        },
      }
    },
  },
}
</script>
