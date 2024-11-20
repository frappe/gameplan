<template>
  <div>
    <TeamHeader :teamId="team.doc?.name" />
    <div class="mx-auto max-w-4xl sm:px-5">
      <div class="mt-6 flex items-center justify-between px-3">
        <TabButtons :buttons="tabOptions" v-model="currentTab" />
        <Dropdown
          placement="right"
          :button="{ icon: LucideSettings2 }"
          :options="[
            { group: 'Order by', items: [{ label: 'Recent activity' }, { label: 'Created' }] },
          ]"
        />
      </div>
      <div class="h-full w-full py-6">
        <DiscussionList
          class="-mx-5 sm:mx-0"
          :listOptions="{ filters: { team: team.doc.name } }"
          routeName="ProjectDiscussion"
        />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { Dropdown, TabButtons } from 'frappe-ui'
import { useTeam } from '@/data/teams'
import DiscussionList from '@/components/DiscussionList.vue'
import TeamHeader from './TeamHeader.vue'
import LucideSettings2 from '~icons/lucide/settings-2.vue'

const props = defineProps<{
  teamId: string
}>()
const team = useTeam(props.teamId)

const currentTab = ref('discussions')
const tabOptions = [
  { label: 'Discussions', value: 'discussions' },
  { label: 'Pages', value: 'pages' },
  { label: 'Chat', value: 'chat' },
]
</script>
