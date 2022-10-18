<template>
  <div class="flex h-full flex-col">
    <div class="flex min-h-0 flex-1">
      <div class="w-full py-6">
        <div class="flex items-center justify-between">
          <h1 class="text-2xl font-semibold">People</h1>
          <div class="flex items-center space-x-2">
            <Input
              class="hidden sm:block"
              type="text"
              placeholder="Search by name"
              v-model="search"
              :debounce="500"
              @input="search = $event"
            />
            <Input
              type="select"
              :options="[
                { label: 'Sort by name', value: 'full_name asc' },
                { label: 'Sort by last updated', value: 'modified desc' },
              ]"
              v-model="orderBy"
            />
          </div>
        </div>
        <div>
          <Input
            class="mt-2 w-full sm:hidden"
            type="text"
            placeholder="Search by name"
            v-model="search"
            :debounce="500"
            @input="search = $event"
          />
        </div>
        <div class="mt-6 grid gap-4 md:grid-cols-3">
          <router-link
            v-for="user in people"
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
            <UserAvatar :user="user.user" size="lg" />
            <div class="ml-3">
              <div class="text-base font-medium text-gray-900">
                {{ $user(user.user).full_name }}
              </div>
              <div class="text-base text-gray-600">{{ user.bio }}</div>
            </div>
          </router-link>

          <div class="p-3" v-if="$resources.profiles.hasNextPage">
            <Button
              @click="$resources.profiles.next()"
              :loading="$resources.profiles.list.loading"
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
import { Badge, Input } from 'frappe-ui'
import Breadcrumbs from '@/components/Breadcrumbs.vue'

export default {
  name: 'People',
  props: ['person'],
  components: { Breadcrumbs, Badge, Input },
  data() {
    return {
      search: '',
      orderBy: 'modified desc',
    }
  },
  resources: {
    profiles() {
      return {
        type: 'list',
        cache: 'People',
        doctype: 'Team User Profile',
        filters: { enabled: 1 },
        fields: ['name', 'user', 'bio', 'modified'],
        limit: 999,
        order_by: this.orderBy,
      }
    },
  },
  computed: {
    people() {
      if (!this.profiles.length) return []
      let myProfile = this.profiles.find((p) => p.user == this.$user().name)
      if (this.search) {
        return this.profiles.filter((p) => {
          return (
            p.full_name.toLowerCase().includes(this.search.toLowerCase()) ||
            p.email.toLowerCase().includes(this.search.toLowerCase())
          )
        })
      }
      return [myProfile, ...this.profiles.filter((p) => p != myProfile)].filter(
        Boolean
      )
    },
    profiles() {
      return (this.$resources.profiles.data || []).map((profile) => {
        return {
          ...profile,
          email: this.$user(profile.user).email,
          full_name: this.$user(profile.user).full_name,
        }
      })
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
