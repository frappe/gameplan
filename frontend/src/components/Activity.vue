<template>
  <div class="relative flex items-center py-4 text-base text-gray-900">
    <FeatherIconCircle
      class="mr-3"
      :name="
        {
          'Discussion Closed': 'lock',
          'Discussion Reopened': 'unlock',
          'Discussion Title Changed': 'edit-3',
          'Discussion Pinned': 'arrow-up-left',
          'Discussion Unpinned': 'arrow-down-left',
        }[activity.action]
      "
      color="green"
    />
    <p>
      <UserInfo :email="activity.user" v-slot="{ user }">
        <UserProfileLink
          class="font-medium hover:text-blue-600"
          :user="user.name"
        >
          {{ user.full_name }}
        </UserProfileLink>
      </UserInfo>
      <span class="text-gray-900" v-if="activity.action == 'Discussion Closed'">
        closed this discussion
      </span>
      <span
        class="text-gray-900"
        v-if="activity.action == 'Discussion Reopened'"
      >
        reopened this discussion
      </span>
      <span class="text-gray-900" v-if="activity.action == 'Discussion Pinned'">
        pinned this discussion
      </span>
      <span
        class="text-gray-900"
        v-if="activity.action == 'Discussion Unpinned'"
      >
        unpinned this discussion
      </span>
      <span
        class="text-gray-900"
        v-if="activity.action == 'Discussion Title Changed'"
      >
        changed the title from "{{ activity.data.old_title }}" to "{{
          activity.data.new_title
        }}"
      </span>
      <time
        class="text-gray-600"
        :datetime="activity.creation"
        :title="$dayjs(activity.creation)"
      >
        {{ $dayjs(activity.creation).fromNow() }}
      </time>
    </p>
  </div>
</template>
<script>
import UserProfileLink from './UserProfileLink.vue'
import FeatherIconCircle from './FeatherIconCircle.vue'
export default {
  name: 'Activity',
  props: {
    activity: {
      type: Object,
      required: true,
    },
  },
  components: { UserProfileLink, FeatherIconCircle },
}
</script>
