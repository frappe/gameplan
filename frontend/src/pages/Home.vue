<template>
  <div class="flex h-full flex-col">
    <div class="flex flex-1">
      <div class="h-full w-full">
        <div
          class="sticky top-0 z-10 mb-1 sm:mb-5 flex items-center border-b bg-white py-3 px-4 sm:px-5"
        >
          <h1 class="text-2xl font-semibold">Posts</h1>
          <div class="relative ml-auto">
            <FeatherIcon
              name="layers"
              class="absolute my-1.5 ml-2 h-4 w-4 text-gray-500"
            />
            <select class="form-select pl-8" v-model="selectedTeam.value">
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
        </div>
        <DiscussionList
          class="mx-auto max-w-4xl sm:px-5"
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
