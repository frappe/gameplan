<template>
  <div class="flex h-full flex-col">
    <div class="flex flex-1">
      <div class="w-full">
        <PageHeaderMobile class="sm:hidden" title="People">
          <template #prefix>
            <PageHeaderBackButton :to="{ name: 'More' }" />
          </template>
          <template #suffix>
            <Button
              v-if="isAdmin"
              variant="ghost"
              size="md"
              icon="lucide-user-plus-2"
              label="Invite"
              @click="showSettingsDialog('Users')"
            />
          </template>
        </PageHeaderMobile>
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
            <!-- Desktop: header + numeric columns. The avatar gets its own track so
                 the inset divider starts at the name text (grid line 2). -->
            <List
              class="max-sm:hidden list-gap-3"
              :columns="['2.5rem', 'minmax(8rem,1fr)', '6.25rem', '6.25rem', '6.25rem', '6.25rem']"
              divider="inset"
            >
              <!-- px-3 matches the interactive rows' default horizontal padding. -->
              <ListHeader class="px-3">
                <ListHeaderCell class="col-span-2">Member</ListHeaderCell>
                <ListHeaderCell class="justify-end">Posts</ListHeaderCell>
                <ListHeaderCell class="justify-end">Replies</ListHeaderCell>
                <ListHeaderCell class="justify-end">
                  <template #prefix>
                    <ReactionFaceIcon class="size-4 text-ink-gray-5" aria-hidden="true" />
                  </template>
                  Received
                </ListHeaderCell>
                <ListHeaderCell class="justify-end">
                  <template #prefix>
                    <ReactionFaceIcon class="size-4 text-ink-gray-5" aria-hidden="true" />
                  </template>
                  Given
                </ListHeaderCell>
              </ListHeader>
              <ListRow
                v-for="user in people"
                :key="user.name"
                :to="{
                  name: 'PersonProfileProfile',
                  params: {
                    personId: user.name,
                  },
                }"
                class="h-15"
              >
                <ListCell>
                  <UserAvatarWithHover :user="user.user" size="2xl" />
                </ListCell>
                <ListCell>
                  <div class="min-w-0 flex-1">
                    <div class="flex items-center space-x-2">
                      <div class="text-base-medium text-ink-gray-8">
                        {{ $user(user.user).full_name }}
                      </div>
                      <Badge v-if="$user(user.user).isGuest">Guest</Badge>
                    </div>
                    <div
                      v-if="user.bio"
                      class="mt-1.5 min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-base text-ink-gray-5"
                    >
                      {{ user.bio }}
                    </div>
                  </div>
                </ListCell>
                <ListCell class="justify-end">
                  <router-link
                    class="text-base text-ink-gray-5 hover:text-ink-gray-8"
                    :to="{
                      name: 'PersonProfilePosts',
                      params: { personId: user.name },
                    }"
                    @click.prevent
                  >
                    {{ user.discussions_count }}
                  </router-link>
                </ListCell>
                <ListCell class="justify-end">
                  <router-link
                    class="text-base text-ink-gray-5 hover:text-ink-gray-8"
                    :to="{
                      name: 'PersonProfileReplies',
                      params: { personId: user.name },
                    }"
                    @click.prevent
                  >
                    {{ user.comments_count }}
                  </router-link>
                </ListCell>
                <ListCell class="justify-end text-base text-ink-gray-5">
                  {{ user.reactions_received }}
                </ListCell>
                <ListCell class="justify-end text-base text-ink-gray-5">
                  {{ user.reactions_given }}
                </ListCell>
              </ListRow>
            </List>

            <!-- Mobile: avatar + details, stats inline under the name. The avatar
                 track keeps the inset divider starting at the name text. -->
            <List
              class="sm:hidden list-gap-3"
              :columns="['2.5rem', 'minmax(0,1fr)']"
              divider="inset"
            >
              <ListRow
                v-for="user in people"
                :key="user.name"
                :to="{
                  name: 'PersonProfileProfile',
                  params: {
                    personId: user.name,
                  },
                }"
                class="py-2"
              >
                <ListCell>
                  <UserAvatarWithHover :user="user.user" size="2xl" />
                </ListCell>
                <ListCell>
                  <div class="min-w-0 flex-1">
                    <div class="flex items-center space-x-2">
                      <div class="text-base-medium text-ink-gray-8">
                        {{ $user(user.user).full_name }}
                      </div>
                      <Badge v-if="$user(user.user).isGuest">Guest</Badge>
                    </div>
                    <div
                      v-if="user.bio"
                      class="mt-1.5 min-w-0 overflow-hidden text-ellipsis whitespace-nowrap text-base text-ink-gray-5"
                    >
                      {{ user.bio }}
                    </div>
                    <div class="mt-1.5 flex items-center space-x-1 text-base text-ink-gray-5">
                      <span>{{ user.discussions_count }} posts</span>
                      <span class="text-ink-gray-4">&middot;</span>
                      <span>{{ user.comments_count }} replies</span>
                    </div>
                  </div>
                </ListCell>
              </ListRow>
            </List>

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
import {
  PageHeaderBackButton,
  PageHeaderMobile,
  PageHeader,
  Breadcrumbs,
  Badge,
  Button,
  Input,
  Select,
  TextInput,
  usePageMeta,
} from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow } from 'frappe-ui/list'
import { showSettingsDialog } from '@/components/Settings'
import { isGameplanAdmin } from '@/data/users'
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
    PageHeaderBackButton,
    PageHeaderMobile,
    PageHeader,
    ReactionFaceIcon,
    List,
    ListCell,
    ListHeader,
    ListHeaderCell,
    ListRow,
  },
  data() {
    return {
      search: '',
      orderBy: 'modified desc',
    }
  },
  setup() {
    usePageMeta(() => ({ title: 'People' }))
    return {
      showSettingsDialog,
      isAdmin: computed(() => isGameplanAdmin()),
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
      let myProfile = this.profiles.find((p) => p.user == this.$user().name)
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
        .filter((profile) => this.$user(profile.user).isNotGuest)
        .map((profile) => {
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
}
</script>
