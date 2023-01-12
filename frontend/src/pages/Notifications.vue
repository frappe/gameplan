<template>
  <div class="h-full w-full px-4 py-3 sm:px-5">
    <div class="mb-5 flex items-center justify-between">
      <h1 class="text-2xl font-semibold">Notifications</h1>
      <div class="flex items-stretch space-x-2">
        <Button
          @click="$resources.markAllAsRead.submit"
          :loading="$resources.markAllAsRead.loading"
          v-if="
            activeTab === 'Unread' &&
            $resources.unreadNotifications.data?.length > 0
          "
        >
          Mark all as read
        </Button>
        <TabButtons
          :buttons="[{ label: 'Unread', active: true }, { label: 'Read' }]"
          v-model="activeTab"
        />
      </div>
    </div>
    <div class="divide-y">
      <div
        class="flex items-start justify-between py-2"
        v-for="d in notifications"
        :key="d.name"
      >
        <div class="flex items-start space-x-2">
          <UserAvatar size="sm" :user="d.from_user" v-if="d.from_user" />
          <div
            class="grid h-5 w-5 place-items-center"
            v-if="d.type === 'Reaction'"
          >
            <FeatherIcon name="heart" class="h-4 w-4 text-gray-700" />
          </div>
          <div class="text-base text-gray-900">
            {{ d.message }} {{ $dayjs(d.creation).fromNow() }}
          </div>
        </div>
        <div class="ml-2 flex shrink-0 items-start space-x-2">
          <router-link
            v-if="d.discussion || d.task"
            class="block text-sm font-medium text-blue-500 hover:text-blue-700"
            :to="
              d.discussion
                ? {
                    name: 'ProjectDiscussion',
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
            class="rounded p-0.5 transition-colors hover:bg-gray-100"
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
  pageMeta() {
    return {
      title: 'Notifications',
      emoji: '🔔',
    }
  },
  components: { TabButtons, Tooltip, Link },
  resources: {
    unreadNotifications() {
      if (this.activeTab !== 'Unread') return
      return {
        type: 'list',
        cache: 'Unread Notifications',
        doctype: 'GP Notification',
        filters: { to_user: this.$user().name, read: 0 },
        fields: [
          'name',
          'from_user',
          'message',
          'read',
          'type',
          'creation',
          'comment',
          'discussion',
          'task',
          'project',
          'team',
        ],
        orderBy: 'creation desc',
        auto: true,
      }
    },
    readNotifications() {
      if (this.activeTab !== 'Read') return
      return {
        type: 'list',
        cache: 'Read Notifications',
        doctype: 'GP Notification',
        filters: { to_user: this.$user().name, read: 1 },
        fields: [
          'name',
          'from_user',
          'message',
          'read',
          'type',
          'creation',
          'comment',
          'discussion',
          'task',
          'project',
          'team',
        ],
        orderBy: 'creation desc',
        auto: true,
      }
    },
    markAllAsRead() {
      return {
        url: 'gameplan.api.mark_all_notifications_as_read',
        onSuccess() {
          this.$getResource('Unread Notifications Count')?.reload()
          this.$resources.unreadNotifications.reload()
        },
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
