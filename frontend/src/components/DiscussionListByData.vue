<template>
  <div class="h-full">
    <router-link
      v-for="(d, index) in discussions"
      :key="d.name"
      :to="{
        name: 'ProjectDiscussion',
        params: {
          teamId: d.team,
          projectId: d.project,
          postId: d.name,
          slug: d.slug,
        },
      }"
      class="group relative block h-15 rounded-[10px] transition hover:bg-gray-100"
    >
      <div class="flex h-full items-center space-x-4 overflow-hidden px-3 py-2">
        <UserInfo :email="d.last_post_by || d.owner">
          <template v-slot="{ user }">
            <div class="flex items-center space-x-3">
              <div class="relative flex">
                <UserAvatar :user="d.closed_by || user.name" size="2xl" />
              </div>
            </div>
            <div class="min-w-0 flex-1">
              <div class="flex min-w-0 items-center">
                <div
                  class="overflow-hidden text-ellipsis whitespace-nowrap leading-none text-gray-900'"
                >
                  <span
                    class="overflow-hidden text-ellipsis whitespace-nowrap text-base font-medium"
                  >
                    {{ d.title }}
                  </span>
                </div>
              </div>
              <div class="mt-1.5 flex min-w-0 items-center justify-between">
                <div
                  class="overflow-hidden text-ellipsis whitespace-nowrap text-base text-gray-600"
                >
                  <span>
                    {{ user.full_name }}
                  </span>
                  <template v-if="d.project">
                    <span> in </span>
                    <span>
                      {{ d.team }}
                      <span class="text-gray-500"> &mdash; </span>
                      {{ d.project }}
                    </span>
                  </template>
                </div>
              </div>
            </div>
            <div class="ml-auto">
              <div
                class="shrink-0 whitespace-nowrap text-sm text-gray-600"
                :title="discussionTimestampDescription(d)"
              >
                {{ discussionTimestamp(d) }}
              </div>
              <div class="mt-1.5 flex items-center justify-end space-x-3">
                <Badge>{{ d.comments_count + 1 }}</Badge>
              </div>
            </div>
          </template>
        </UserInfo>
      </div>
      <div
        class="mx-3 h-px border-t border-gray-200"
        v-if="index < discussions?.length - 1"
      ></div>
    </router-link>
    <div class="px-2 sm:px-0">
      <div
        v-if="discussions?.length === 0"
        class="flex flex-col items-center rounded-lg border-2 border-dashed py-8 text-base text-gray-600"
      >
        <LucideCoffee class="h-7 w-7 text-gray-500" />
        No discussions
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DiscussionListByData',
  props: {
    discussions: {
      type: Array,
      required: true,
    },
  },
  methods: {
    discussionTimestamp(discussion) {
      let timestamp = discussion.last_post_at || discussion.creation
      if (this.$dayjs().diff(timestamp, 'day') < 25) {
        return this.$dayjs(timestamp).fromNow()
      }
      if (this.$dayjs().diff(timestamp, 'year') < 1) {
        return this.$dayjs(timestamp).format('D MMM')
      }
      return this.$dayjs(timestamp).format('D MMM YYYY')
    },
    discussionTimestampDescription(discussion) {
      return [
        `First Post: ${this.$dayjs(discussion.creation)}`,
        `Latest Post: ${this.$dayjs(discussion.last_post_at)}`,
      ].join('\n')
    },
  },
}
</script>
