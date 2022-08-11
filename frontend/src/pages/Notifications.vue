<template>
  <div class="w-full h-full p-6 overflow-auto">
    <div class="flex items-center justify-between mb-5">
      <h1 class="text-2xl font-semibold">Notifications</h1>
      <div class="flex items-stretch space-x-2">
        <TabButtons
          :buttons="[{ label: 'Unread', active: true }, { label: 'Read' }]"
          v-model="activeTab"
        />
      </div>
    </div>
    <div class="divide-y">
      <div
        class="flex items-center justify-between py-2"
        v-for="d in notifications"
        :key="d.name"
      >
        <div class="flex items-center">
          <Avatar
            size="sm"
            :imageURL="$user(d.from_user).user_image"
            :label="$user(d.from_user).full_name"
          />
          <div class="ml-2 text-base text-gray-900">
            {{ d.message }} {{ $dayjs(d.creation).fromNow() }}
          </div>
        </div>
        <div class="flex items-center space-x-2">
          <router-link
            v-if="d.discussion || d.task"
            class="block text-sm font-medium text-blue-500 hover:text-blue-700"
            :to="
              d.discussion
                ? {
                    name: 'ProjectDetailDiscussion',
                    params: {
                      postId: d.discussion,
                      projectId: d.project,
                      teamId: d.team,
                    },
                    query: d.comment ? { comment: d.comment } : null,
                  }
                : d.task
                ? {
                    name: 'ProjectTaskDetail',
                    params: {
                      teamId: d.team,
                      projectId: d.project,
                      taskId: d.task,
                    },
                    query: d.comment ? { comment: d.comment } : null,
                  }
                : null
            "
            @click="markAsRead(d.name)"
          >
            {{ d.discussion ? 'View Discussion' : d.task ? 'View Task' : '' }}
          </router-link>
          <button
            v-if="!d.read"
            class="p-0.5 transition-colors rounded hover:bg-gray-100"
            @click="markAsRead(d.name)"
            title="Mark as read"
          >
            <FeatherIcon name="x" class="w-4" />
          </button>
        </div>
      </div>
    </div>
    <div v-if="!notifications?.length" class="text-base text-gray-600">
      Nothing to see here
    </div>
  </div>
</template>
<script>
import Avatar from 'frappe-ui/src/components/Avatar.vue'
import TabButtons from '../components/TabButtons.vue'
import Tooltip from 'frappe-ui/src/components/Tooltip.vue'
import Link from '@/components/Link.vue'

export default {
  name: 'Notifications',
  data() {
    return {
      activeTab: 'Unread',
    }
  },
  components: { Avatar, TabButtons, Tooltip, Link },
  resources: {
    unreadNotifications() {
      if (this.activeTab !== 'Unread') return
      return {
        type: 'list',
        cache: 'Unread Notifications',
        doctype: 'Team Notification',
        filters: { to_user: this.$user().name, read: 0 },
        fields: [
          'name',
          'from_user',
          'message',
          'read',
          'creation',
          'comment',
          'discussion',
          'task',
          'project',
          'team',
        ],
        order_by: 'creation desc',
      }
    },
    readNotifications() {
      if (this.activeTab !== 'Read') return
      return {
        type: 'list',
        cache: 'Read Notifications',
        doctype: 'Team Notification',
        filters: { to_user: this.$user().name, read: 1 },
        fields: [
          'name',
          'from_user',
          'message',
          'read',
          'creation',
          'comment',
          'discussion',
          'task',
          'project',
          'team',
        ],
        order_by: 'creation desc',
      }
    },
  },
  computed: {
    notifications() {
      return this.activeTab === 'Unread'
        ? this.$resources.unreadNotifications.data
        : this.$resources.readNotifications.data
    },
  },
  methods: {
    markAsRead(name) {
      this.$resources.unreadNotifications.setValue.submit(
        {
          name,
          read: 1,
        },
        {
          onSuccess: () => {
            this.$getResource('Unread Notifications Count')?.reload()
          },
        }
      )
    },
  },
  mounted() {
    this.$getResource('Unread Notifications Count')?.reload()
  },
}
</script>
