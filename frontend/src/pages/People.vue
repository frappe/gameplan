<template>
  <div class="flex h-full flex-col">
    <div class="flex flex-1">
      <div class="w-full">
        <header class="sticky top-0 z-10 border-b bg-white py-3 px-4 sm:px-5">
          <div class="flex items-center justify-between">
            <h1 class="text-2xl font-semibold">People</h1>
            <div class="flex items-center space-x-2">
              <Input
                class="hidden sm:block"
                type="text"
                icon-left="search"
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
        </header>
        <div
          class="grid gap-5 py-4 px-4 sm:py-5 sm:px-5 lg:grid-cols-3 xl:grid-cols-4"
        >
          <router-link
            v-for="user in people"
            :key="user.name"
            :to="{
              name: 'PersonProfile',
              params: {
                personId: user.name,
              },
            }"
            class="w-full items-center overflow-hidden rounded-[20px] border pb-4 hover:border-gray-400 focus-visible:border-gray-400 focus-visible:outline-none focus-visible:ring focus-visible:ring-gray-300"
            exact-active-class="!bg-gray-100"
          >
            <div class="h-16 w-full bg-gray-50">
              <img
                v-if="user.cover_image"
                class="h-16 w-full object-cover"
                loading="lazy"
                :src="coverImageUrl(user.cover_image)"
                :style="{
                  objectPosition: `center ${user.cover_image_position}%`,
                }"
              />
            </div>
            <div class="-mt-8 flex justify-center">
              <UserImage
                v-if="$user(user.user).user_image"
                :user="user.user"
                class="h-16 w-16 rounded-full border-[6px] border-white object-cover"
              />
              <div
                v-else
                class="h-16 w-16 rounded-full border-[6px] border-white bg-gray-100"
              ></div>
            </div>
            <div class="px-1 text-center">
              <div class="text-xl font-medium text-gray-900">
                {{ $user(user.user).full_name }}
              </div>
              <div
                class="overflow-hidden text-ellipsis whitespace-nowrap text-lg text-gray-600"
                :title="(user.bio || '').length > 40 ? user.bio : ''"
              >
                {{ user.bio }}
              </div>
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
        doctype: 'GP User Profile',
        filters: { enabled: 1 },
        fields: [
          'name',
          'user',
          'bio',
          'modified',
          'cover_image',
          'cover_image_position',
        ],
        pageLength: 999,
        orderBy: this.orderBy,
        auto: true,
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
  methods: {
    coverImageUrl(url) {
      if (!url) return null
      if (url.startsWith('https://images.unsplash.com')) {
        return url + '&w=300&fit=crop&crop=entropy,faces,focalpoint'
      }
      return url
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
