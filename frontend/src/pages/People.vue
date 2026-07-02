<template>
  <div class="flex h-full flex-col">
    <div class="flex flex-1">
      <div class="w-full">
        <MobileHeader class="sm:hidden" title="People">
          <template #left>
            <MobileBackButton :to="{ name: 'More' }" />
          </template>
          <template #right>
            <Button
              v-if="isAdmin"
              variant="ghost"
              size="md"
              icon="lucide-user-plus-2"
              label="Invite"
              @click="showSettingsDialog('Users')"
            />
          </template>
        </MobileHeader>
        <PageHeader class="hidden sm:flex">
          <Breadcrumbs :items="[{ label: 'People', route: { name: 'People' } }]" />
          <div class="h-7"></div>
        </PageHeader>
        <div class="mx-auto w-full body-container pt-6">
          <div class="flex items-center justify-between">
            <h2 class="text-3xl-semibold text-ink-gray-7">{{ people.length }} members</h2>
            <div class="flex items-center gap-2">
              <TextInput
                class="hidden sm:block"
                type="text"
                placeholder="Search"
                v-model="search"
                :debounce="500"
              >
                <template #prefix>
                  <span class="lucide-search w-4 text-ink-gray-5" />
                </template>
              </TextInput>
              <Select
                class="!w-fit"
                :options="[
                  { label: 'Name', value: 'full_name asc' },
                  { label: 'Last updated', value: 'modified desc' },
                  { label: 'Posts', value: 'posts' },
                  { label: 'Replies', value: 'replies' },
                  { label: 'Reactions received', value: 'reactions_received' },
                ]"
                v-model="orderBy"
              >
                <template #prefix>
                  <span class="lucide-arrow-down-up w-4 text-ink-gray-5" />
                </template>
              </Select>
              <Button
                v-if="isAdmin"
                class="hidden sm:inline-flex"
                variant="solid"
                icon-left="lucide-user-plus-2"
                @click="showSettingsDialog('Users')"
              >
                Invite
              </Button>
            </div>
          </div>
          <div class="sm:hidden mt-4">
            <TextInput
              class="w-full"
              type="text"
              placeholder="Search"
              v-model="search"
              :debounce="500"
            >
              <template #prefix>
                <span class="lucide-search w-4 text-ink-gray-5" />
              </template>
            </TextInput>
          </div>
          <div class="mt-4 pb-16 -mx-3">
            <div
              class="hidden h-8 items-center px-3 text-sm text-ink-gray-5 sm:grid sm:grid-cols-[minmax(8rem,1fr)_repeat(4,5.5rem)] sm:gap-6"
            >
              <div>Member</div>
              <div class="text-right">Posts</div>
              <div class="text-right">Replies</div>
              <div class="flex items-center justify-end gap-1.5">
                <ReactionFaceIcon class="size-4 text-ink-gray-5" aria-hidden="true" />
                <span>Received</span>
              </div>
              <div class="flex items-center justify-end gap-1.5">
                <ReactionFaceIcon class="size-4 text-ink-gray-5" aria-hidden="true" />
                <span>Given</span>
              </div>
            </div>
            <template v-for="user in people" :key="user.name">
              <router-link
                :to="{
                  name: 'PersonProfileProfile',
                  params: {
                    personId: user.name,
                  },
                }"
                class="flex sm:grid sm:grid-cols-[minmax(8rem,1fr)_repeat(4,5.5rem)] sm:gap-6 sm:items-center sm:rounded px-3 py-2 sm:h-15 sm:hover:bg-surface-gray-2 duration-150 active:bg-surface-gray-2 transition-colors"
                exact-active-class="!bg-surface-gray-2"
              >
                <div class="flex w-full min-w-0 items-center">
                  <UserAvatarWithHover :user="user.user" size="2xl" />
                  <div class="ml-3 min-w-0 flex-1">
                    <div class="flex items-center space-x-2">
                      <div class="text-base-medium text-ink-gray-8">
                        {{ useUser(user.user).full_name }}
                      </div>
                      <Badge v-if="useUser(user.user).isGuest">Guest</Badge>
                    </div>
                    <div
                      v-if="user.bio"
                      class="mt-1.5 min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-base text-ink-gray-5"
                    >
                      {{ user.bio }}
                    </div>
                    <div
                      class="sm:hidden mt-1.5 flex items-center space-x-1 text-base text-ink-gray-5"
                    >
                      <span>{{ user.discussions_count }} posts</span>
                      <span class="text-ink-gray-4">&middot;</span>
                      <span>{{ user.comments_count }} replies</span>
                    </div>
                  </div>
                </div>
                <router-link
                  class="hidden items-center justify-end text-base text-ink-gray-5 hover:text-ink-gray-8 sm:flex"
                  :to="{
                    name: 'PersonProfilePosts',
                    params: { personId: user.name },
                  }"
                  @click.prevent
                >
                  {{ user.discussions_count }}
                </router-link>
                <router-link
                  class="hidden items-center justify-end text-base text-ink-gray-5 hover:text-ink-gray-8 sm:flex"
                  :to="{
                    name: 'PersonProfileReplies',
                    params: { personId: user.name },
                  }"
                  @click.prevent
                >
                  {{ user.comments_count }}
                </router-link>
                <span class="hidden items-center justify-end text-base text-ink-gray-5 sm:flex">
                  {{ user.reactions_received }}
                </span>
                <span class="hidden items-center justify-end text-base text-ink-gray-5 sm:flex">
                  {{ user.reactions_given }}
                </span>
              </router-link>
              <div class="mx-2 border-b"></div>
            </template>
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
  </div>
</template>
<script>
import { computed } from 'vue'
import { Breadcrumbs, Badge, Button, Input, Select, TextInput } from 'frappe-ui'
import MobileBackButton from '@/components/MobileBackButton.vue'
import MobileHeader from '@/components/MobileHeader.vue'
import PageHeader from '@/components/PageHeader.vue'
import { showSettingsDialog } from '@/components/Settings'
import { isGameplanAdmin, useSessionUser, useUser } from '@/data/users'
import UserAvatarWithHover from '@/components/UserAvatarWithHover.vue'
import ReactionFaceIcon from '@/components/ReactionFaceIcon.vue'

export default {
  name: 'People',
  props: ['person'],
  components: {
    Badge,
    Button,
    Input,
    TextInput,
    Select,
    Breadcrumbs,
    MobileBackButton,
    MobileHeader,
    PageHeader,
    ReactionFaceIcon,
  },
  data() {
    return {
      search: '',
      orderBy: 'modified desc',
    }
  },
  setup() {
    return {
      showSettingsDialog,
      isAdmin: computed(() => isGameplanAdmin()),
      useUser,
    }
  },
  resources: {
    profiles() {
      let orderBy = this.orderBy
      if (['posts', 'replies', 'reactions_received'].includes(orderBy)) {
        orderBy = 'modified desc'
      }
      return {
        type: 'list',
        url: '/api/method/gameplan.gameplan.doctype.gp_user_profile.gp_user_profile.get_list',
        cache: ['People', orderBy],
        doctype: 'GP User Profile',
        filters: { enabled: 1 },
        fields: ['name', 'user', 'bio', 'modified', 'cover_image', 'cover_image_position'],
        pageLength: 999,
        orderBy: this.orderBy,
        auto: true,
      }
    },
  },
  computed: {
    people() {
      if (!this.profiles.length) return []
      let myProfile = this.profiles.find((p) => p.user == useSessionUser().name)
      if (this.search) {
        return this.profiles.filter((p) => {
          return (
            p.full_name.toLowerCase().includes(this.search.toLowerCase()) ||
            p.email.toLowerCase().includes(this.search.toLowerCase())
          )
        })
      }

      let list = [myProfile, ...this.profiles.filter((p) => p != myProfile)].filter(Boolean)

      if (this.orderBy == 'posts') {
        list = list.sort((a, b) => b.discussions_count - a.discussions_count)
      } else if (this.orderBy == 'replies') {
        list = list.sort((a, b) => b.comments_count - a.comments_count)
      } else if (this.orderBy == 'reactions_received') {
        list = list.sort((a, b) => b.reactions_received - a.reactions_received)
      }
      return list
    },
    profiles() {
      return (this.$resources.profiles.data || [])
        .filter((profile) => useUser(profile.user).isNotGuest)
        .map((profile) => {
          return {
            ...profile,
            email: useUser(profile.user).email,
            full_name: useUser(profile.user).full_name,
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
    }
  },
}
</script>
