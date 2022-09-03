<template>
  <div class="flex h-full flex-col">
    <div class="flex min-h-0 flex-1">
      <div class="w-full py-6">
        <div class="flex items-center justify-between">
          <h1 class="text-2xl font-semibold">People</h1>
          <Input
            type="text"
            placeholder="Search by name"
            v-model="search"
            :debounce="500"
            @input="search = $event"
          />
        </div>
        <div class="mt-6 grid md:grid-cols-3 gap-4">
          <router-link
            v-for="user in $resources.users.data"
            :key="user.name"
            :to="{
              name: 'PersonProfile',
              params: {
                personId: user.name,
              },
            }"
            class="flex w-full items-center rounded-lg border p-3 hover:bg-gray-50 focus-visible:border-gray-400 focus-visible:outline-none focus-visible:ring focus-visible:ring-gray-300"
            exact-active-class="!bg-gray-100"
          >
            <Avatar
              :label="user.full_name"
              :imageURL="user.user_image"
              size="lg"
            />
            <div class="ml-3">
              <div class="text-base font-medium text-gray-900">
                {{ user.full_name }}
              </div>
              <div class="text-base text-gray-600">{{ user.email }}</div>
            </div>
          </router-link>

          <div class="p-3" v-if="$resources.users.hasNextPage">
            <Button
              @click="$resources.users.next()"
              :loading="$resources.users.list.loading"
            >
              Load more
            </Button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
import { Avatar, Badge, Input } from 'frappe-ui'
import Breadcrumbs from '@/components/Breadcrumbs.vue'

export default {
  name: 'People',
  props: ['person'],
  components: { Breadcrumbs, Avatar, Badge, Input },
  data() {
    return {
      search: '',
    }
  },
  resources: {
    users() {
      let filters = { enabled: 1 }
      if (this.search) {
        filters = { full_name: ['like', '%' + this.search + '%'] }
      }
      return {
        type: 'list',
        cache: 'People',
        doctype: 'Team User Profile',
        filters,
        fields: [
          'name',
          'user',
          'user.full_name',
          'user.email',
          'user.user_image',
          'status',
        ],
        limit: 999,
      }
    },
  },
  pageMeta() {
    return {
      title: 'People',
      emoji: '👨‍👩‍👧‍👦',
    }
  },
}
</script>
