<template>
  <div class="flex flex-col h-full">
    <div class="flex flex-1 min-h-0">
      <div class="w-full" v-if="!selectedUser">
        <div class="py-6 space-y-2">
          <div class="flex items-center justify-between">
            <h1 class="text-2xl font-semibold">People</h1>
            <Input type="text" placeholder="Search by name" v-model="search" />
          </div>
          <div class="divide-y">
            <div v-for="user in $resources.users.data" :key="user.name">
              <router-link
                :to="{
                  name: 'People',
                  params: {
                    person: $user().name === user.user ? 'profile' : user.name,
                  },
                }"
                class="flex items-center w-full p-3 hover:bg-gray-50"
                exact-active-class="!bg-gray-100"
              >
                <Avatar :label="user.full_name" :imageURL="user.user_image" />
                <div class="ml-2">
                  <div class="text-lg text-gray-900">{{ user.full_name }}</div>
                  <div class="text-base text-gray-600">{{ user.email }}</div>
                </div>
                <Badge
                  class="ml-auto"
                  :class="$route.params.person === user.name ? 'bg-white' : ''"
                  :color="{
                    green: user.status == 'Available',
                    yellow: user.status == 'Away',
                    red: user.status == 'Busy',
                  }"
                >
                  {{ user.status }}
                </Badge>
              </router-link>
            </div>
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
      <div class="w-full" v-else>
        <PeopleProfile :user="selectedUser" />
      </div>
    </div>
  </div>
</template>
<script>
import { Avatar, Badge, Input } from 'frappe-ui'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import PeopleProfile from './PeopleProfile.vue'

export default {
  name: 'People',
  props: ['person'],
  components: { Breadcrumbs, Avatar, PeopleProfile, Badge, Input },
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
      }
    },
  },
  computed: {
    selectedUser() {
      if (!this.$resources.users.data) return

      if (this.person === 'profile') {
        let user = this.$resources.users.data.find(
          (d) => d.user === this.$user().name
        )
        return user?.name
      }
      return this.person
    },
  },
  pageMeta() {
    let selectedPerson = (this.$resources.users.data || []).find(
      (d) => d.name === this.person
    )
    return {
      title:
        'People' + (selectedPerson ? ' - ' + selectedPerson.full_name : ''),
      emoji: '👨‍👩‍👧‍👦',
    }
  },
}
</script>
