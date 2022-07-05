<template>
  <div class="flex flex-col h-full">
    <div class="flex flex-1 min-h-0">
      <div class="w-5/12 h-full px-6 py-6 overflow-auto">
        <div class="flex items-center justify-between mb-5">
          <h1 class="text-2xl font-semibold">Posts</h1>

          <select class="form-input" v-model="selectedTeam.value">
            <option value="" selected>Posts by all teams</option>
            <option selected disabled>Filter by Team</option>
            <option
              v-for="team in $getListResource('Sidebar Teams').data"
              :key="team.name"
              :value="team.name"
            >
              {{ team.title }}
            </option>
          </select>
        </div>
        <DiscussionList
          routeName="Home"
          :filters="selectedTeam.value ? { team: selectedTeam.value } : null"
        />
      </div>
      <div class="w-7/12 overflow-auto border-l">
        <DiscussionView :postId="postId" />
      </div>
    </div>
  </div>
</template>
<script>
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import DiscussionList from '@/components/DiscussionList.vue'
import DiscussionView from '@/components/DiscussionView.vue'
export default {
  name: 'Home',
  props: ['postId'],
  components: { Breadcrumbs, DiscussionList, DiscussionView },
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
