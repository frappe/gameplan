<template>
  <div class="max-w-4xl mx-auto px-5">
    <div class="flex mt-5 mb-4">
      <TabButtons :buttons="spaceTabs" v-model="currentTab" />
    </div>
    <DiscussionList
      :listOptions="{ filters: { project: space.doc.name } }"
      routeName="ProjectDiscussion"
    />
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { Breadcrumbs, TabButtons } from 'frappe-ui'
import DiscussionList from '@/components/DiscussionList.vue'
import PageHeader from '@/components/PageHeader.vue'

const props = defineProps<{
  space: Object
}>()

const spaceTabs = [
  { label: 'Discussions', value: 'discussions' },
  { label: 'Pages', value: 'pages' },
  { label: 'Tasks', value: 'tasks' },
]

const currentTab = ref('discussions')
</script>
