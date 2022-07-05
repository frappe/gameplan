<template>
  <div class="flex flex-col h-full">
    <div class="flex flex-1 min-h-0">
      <div class="w-1/3 overflow-auto">
        <div class="py-6 pl-6 space-y-2">
          <h1 class="mb-6 text-6xl font-bold leading-7 text-gray-900">
            People
          </h1>
          <div v-for="user in $resources.users.data" :key="user.name">
            <router-link
              :to="{
                name: 'People',
                params: {
                  person: $user().name === user.user ? 'profile' : user.name,
                },
              }"
              class="flex items-center w-full p-4 border rounded-xl hover:bg-gray-50"
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
        </div>
      </div>
      <div class="w-2/3 overflow-auto">
        <PeopleProfile v-if="selectedUser" :user="selectedUser" />
      </div>
    </div>
  </div>
</template>
<script>
import { Avatar, Badge } from 'frappe-ui'
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import PeopleProfile from './PeopleProfile.vue'

export default {
  name: 'People',
  props: ['person'],
  components: { Breadcrumbs, Avatar, PeopleProfile, Badge },
  resources: {
    users() {
      return {
        type: 'list',
        doctype: 'Team User Profile',
        cache: 'People',
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
