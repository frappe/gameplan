<template>
  <div class="flex items-center space-x-2">
    <Input
      iconLeft="search"
      class="w-full"
      placeholder="Type a query and hit enter to search"
      autocomplete="off"
      :value="query"
      @input="query = $event"
      @keydown.enter="
        (e) =>
          e.target.value ? $resources.search.submit(e.target.value) : null
      "
      v-focus
    />
    <Button
      @click="$resources.search.submit(query)"
      :loading="$resources.search.loading"
    >
      Search
    </Button>
  </div>
  <div v-if="$resources.search.data" class="mt-2 text-sm text-gray-600">
    About {{ $resources.search.data.total }} results for "{{
      $resources.search.params.query
    }}" ({{ $resources.search.data.duration.toFixed(2) }}
    ms)
  </div>
  <div class="mt-6 divide-y" v-if="$resources.search.data?.docs.length">
    <router-link
      class="flex p-3 hover:bg-gray-100"
      v-for="d in $resources.search.data.docs"
      :to="{
        name: 'ProjectDiscussion',
        params: { teamId: d.team, projectId: d.project, postId: d.name },
        query: { comment: d.comment || undefined, fromSearch: 1 },
      }"
    >
      <UserAvatar :user="d.last_post_by || d.owner" class="mr-4" />
      <div class="search-result">
        <div class="flex items-center">
          <div class="text-lg font-medium leading-snug" v-html="d.title" />
          <span class="whitespace-pre text-gray-600 md:inline"> &middot; </span>
          <span
            class="shrink-0 whitespace-nowrap text-sm text-gray-600 md:inline"
            >{{
              $dayjs().diff(d.last_post_at, 'day') >= 25
                ? $dayjs(d.last_post_at).format('D MMM')
                : $dayjs(d.last_post_at).fromNow()
            }}
          </span>
        </div>
        <div
          class="mt-1 text-base text-gray-800"
          v-html="trimContent(d.content)"
        ></div>
      </div>
    </router-link>
    <Button
      class="mt-4"
      @click="next"
      :loading="$resources.search.loading"
      v-if="$resources.search.data?.docs.length < $resources.search.data.total"
    >
      Load more
    </Button>
  </div>
</template>
<script>
import { focus } from '@/directives'

export default {
  name: 'AppSearch',
  directives: {
    focus,
  },
  data() {
    return {
      start: 0,
      query: '',
    }
  },
  resources: {
    search: {
      cache: 'Search',
      method: 'gameplan.gameplan.doctype.team_discussion.search.search',
      makeParams(query) {
        return { query, start: this.start }
      },
      transform(data) {
        return {
          ...data,
          docs: this.start
            ? this.$resources.search.data.docs.concat(data.docs)
            : data.docs,
        }
      },
    },
  },
  methods: {
    next() {
      this.start += 10
      this.$resources.search.submit(
        this.query || this.$resources.search.params.query
      )
    },
    trimContent(content) {
      let trimmedLength = 200
      let indexOf = content.indexOf('<mark>')
      if (indexOf === -1) {
        return content.slice(0, 200)
      }

      let start = indexOf - trimmedLength / 2
      if (start < 0) {
        start = 0
      }
      let end = indexOf + trimmedLength / 2
      if (end > content.length) {
        end = content.length
      }
      return content.slice(start, end)
    },
  },
}
</script>
<style>
.search-result mark {
  border-radius: 0.25rem;
  background-color: theme('colors.yellow.200');
  padding: 2px 3px;
}
</style>
