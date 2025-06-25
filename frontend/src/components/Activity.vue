<template>
  <div class="relative flex items-center text-p-base">
    <div
      class="mr-3 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-surface-gray-2 text-ink-gray-8"
    >
      <LucideLock class="h-4 w-4" v-if="activity.action === 'Discussion Closed'" />
      <LucideUnlock class="h-4 w-4" v-else-if="activity.action === 'Discussion Reopened'" />
      <LucideEdit3 class="h-4 w-4" v-else-if="activity.action === 'Discussion Title Changed'" />
      <LucideArrowUpLeft class="h-4 w-4" v-else-if="activity.action === 'Discussion Pinned'" />
      <LucideArrowDownLeft class="h-4 w-4" v-else-if="activity.action === 'Discussion Unpinned'" />
      <LucideEdit3 class="h-4 w-4" v-else-if="activity.action === 'Task Value Changed'" />
    </div>
    <p>
      <UserInfo :email="activity.user" v-slot="{ user }">
        <UserProfileLink
          class="font-medium text-ink-gray-7 hover:text-ink-gray-5"
          :user="user.name"
        >
          {{ user.full_name }}
        </UserProfileLink>
      </UserInfo>
      <span class="text-ink-gray-8" v-if="activity.action == 'Discussion Closed'">
        closed this discussion
      </span>
      <span class="text-ink-gray-8" v-if="activity.action == 'Discussion Reopened'">
        reopened this discussion
      </span>
      <span class="text-ink-gray-8" v-if="activity.action == 'Discussion Pinned'">
        pinned this discussion
      </span>
      <span class="text-ink-gray-8" v-if="activity.action == 'Discussion Unpinned'">
        unpinned this discussion
      </span>
      <span class="text-ink-gray-8" v-if="activity.action == 'Discussion Title Changed'">
        changed the title from "{{ activity.data.old_title }}" to "{{ activity.data.new_title }}"
      </span>
      <span class="text-ink-gray-5" v-if="activity.action == 'Task Value Changed'">
        <template v-if="activity.data.field === 'assigned_to'">
          assigned this to
          <UserProfileLink
            class="font-medium text-ink-gray-7 hover:text-ink-gray-5"
            :user="$user(activity.data.new_value).name"
          >
            {{ $user(activity.data.new_value).full_name }}
          </UserProfileLink>
        </template>
        <template v-else-if="activity.data.field === 'description'">
          updated the description
        </template>
        <template v-else-if="activity.data.field === 'project'">
          changed project
          <span v-if="activity.data.old_value">from&nbsp;</span>
          <span class="text-ink-gray-7">
            {{ spaceTitle(activity.data.old_value) }}
          </span>
          to
          <span class="text-ink-gray-7">
            {{ spaceTitle(activity.data.new_value) }}
          </span>
        </template>
        <template v-else>
          changed {{ activity.data.field_label }}
          <span v-if="activity.data.old_value">from&nbsp;</span>
          <span class="text-ink-gray-7">{{ activity.data.old_value }}</span> to
          <span class="text-ink-gray-7">{{ activity.data.new_value }}</span>
        </template> </span
      >&nbsp;
      <Tooltip :text="dayjsLocal(activity.creation).format('D MMM YYYY [at] h:mm A')">
        <time class="text-ink-gray-5" :datetime="activity.creation">
          {{ dayjsLocal(activity.creation).fromNow() }}
        </time>
      </Tooltip>
    </p>
  </div>
</template>
<script setup lang="ts">
import { dayjsLocal, Tooltip } from 'frappe-ui'
import UserProfileLink from './UserProfileLink.vue'
import { spaceTitle } from '@/utils/formatters'

interface Activity {
  action: string
  user: string
  creation: string
  data: {
    old_title?: string
    new_title?: string
    field?: string
    field_label?: string
    old_value?: string
    new_value?: string
  }
}

defineProps<{
  activity: Activity
}>()
</script>
