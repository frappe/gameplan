<template>
  <div class="flex flex-col h-full">
    <div class="flex flex-1 min-h-0">
      <div class="w-full h-full py-6">
        <div class="flex items-center justify-between mb-3">
          <h1 class="text-2xl font-semibold">Posts</h1>

          <select class="form-input" v-model="selectedTeam.value">
            <option value="" selected>Posts by all teams</option>
            <option selected disabled>Filter by Team</option>
            <option
              v-for="team in $getListResource('Teams').data"
              :key="team.name"
              :value="team.name"
            >
              {{ team.title }}
            </option>
          </select>
        </div>
        <DiscussionList
          routeName="ProjectDetailDiscussion"
          :filters="selectedTeam.value ? { team: selectedTeam.value } : null"
        />
      </div>
    </div>
  </div>
</template>
<script>
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import DiscussionList from '@/components/DiscussionList.vue'
export default {
  name: 'Home',
  props: ['postId'],
  components: { Breadcrumbs, DiscussionList },
  data() {
    return {
      selectedTeam: { label: null, value: '' },
    }
  },
  pageMeta() {
    return {
      title: 'Home',
      emoji: '🏠',
    }
  },
}
</script>
