<template>
  <DiscussionList
    class="mx-auto max-w-4xl sm:px-5"
    routeName="ProjectDiscussion"
    :filters="selectedTeam.value ? { team: selectedTeam.value } : null"
  />
</template>
<script>
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import DiscussionList from '@/components/DiscussionList.vue'
import { activeTeams } from '@/data/teams'
import { scrollTo as scrollContainerTo } from '@/utils/scrollContainer'

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
  methods: {
    scrollToTop() {
      scrollContainerTo({
        top: 0,
        behavior: 'smooth',
      })
    },
  },
  pageMeta() {
    return {
      title: 'Home',
    }
  },
}
</script>
