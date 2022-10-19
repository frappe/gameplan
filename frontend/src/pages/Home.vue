<template>
  <div class="flex h-full flex-col">
    <div class="flex min-h-0 flex-1">
      <div class="h-full w-full py-6">
        <div class="mb-3 flex items-center justify-between">
          <h1 class="text-2xl font-semibold">Posts</h1>

          <select class="form-input" v-model="selectedTeam.value">
            <option value="" selected>Posts by all teams</option>
            <option selected disabled>Filter by Team</option>
            <option
              v-for="team in activeTeams"
              :key="team.name"
              :value="team.name"
            >
              {{ team.title }}
            </option>
          </select>
        </div>
        <DiscussionList
          routeName="ProjectDiscussion"
          :filters="selectedTeam.value ? { team: selectedTeam.value } : null"
        />
      </div>
    </div>
  </div>
</template>
<script>
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import DiscussionList from '@/components/DiscussionList.vue'
import { activeTeams } from '@/data/teams'

export default {
  name: 'Home',
  props: ['postId'],
  components: { Breadcrumbs, DiscussionList },
  data() {
    return {
      selectedTeam: { label: null, value: '' },
      activeTeams,
    }
  },
  pageMeta() {
    return {
      title: 'Home',
    }
  },
}
</script>
