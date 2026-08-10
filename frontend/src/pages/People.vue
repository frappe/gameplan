<template>
  <div class="flex h-full flex-col">
    <div class="flex flex-1">
      <div class="w-full">
        <PageHeaderMobile class="sm:hidden" title="People">
          <template #left>
            <PageHeaderBackButton :to="{ name: 'More' }" />
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
        </PageHeaderMobile>
        <PageHeader class="hidden sm:flex">
          <Breadcrumbs :items="[{ label: 'People', route: { name: 'People' } }]" />
          <div class="h-7"></div>
        </PageHeader>
        <div class="mx-auto w-full body-container pt-6">
          <div class="flex items-center justify-between">
            <h2 class="text-3xl-semibold text-ink-gray-7">{{ peopleList.length }} members</h2>
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
              <Select class="!w-fit" :options="orderByOptions" v-model="orderBy">
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
          <div class="mt-4 pb-16 -mx-3" v-show="!listFailure">
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
                v-for="user in peopleList"
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
                v-for="user in peopleList"
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
                    <div class="mt-1.5 flex items-center space-x-1 text-base text-ink-gray-5">
                      <span>{{ user.discussions_count }} posts</span>
                      <span class="text-ink-gray-4">&middot;</span>
                      <span>{{ user.comments_count }} replies</span>
                    </div>
                  </div>
                </ListCell>
              </ListRow>
            </List>

            <EmptyStateBox v-if="isEmpty" class="mt-2">
              <span class="lucide-users mb-1 size-7 text-ink-gray-4" aria-hidden="true" />
              {{ search ? 'No members match your search' : 'No members yet' }}
            </EmptyStateBox>

            <div class="p-3" v-if="people.hasNextPage">
              <Button @click="people.next" :loading="people.loading"> Load more </Button>
            </div>
          </div>

          <!-- The fetch failed and there's no cached page to fall back to (staleOnError
               already covers the case where cached data exists - people.data stays
               non-null then, so listFailure is false and the list above keeps showing
               it). Without this a failed fetch renders as "0 members" - indistinguishable
               from an org with no one in it (US6). -->
          <OfflineContentFallback
            v-if="listFailure"
            class="mx-auto mt-6 max-w-2xl px-6"
            :title="listFailure.title"
            :message="listFailure.message"
            @retry="people.reload()"
          />
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  PageHeaderBackButton,
  PageHeaderMobile,
  PageHeader,
  Breadcrumbs,
  Badge,
  Button,
  Select,
  TextInput,
  usePageMeta,
} from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow } from 'frappe-ui/list'
import { showSettingsDialog } from '@/components/Settings'
import { isGameplanAdmin, useSessionUser, useUser } from '@/data/users'
import { people, peopleOrderBy } from '@/data/people'
import OfflineContentFallback from '@/components/OfflineContentFallback.vue'
import EmptyStateBox from '@/components/EmptyStateBox.vue'
import UserAvatarWithHover from '@/components/UserAvatarWithHover.vue'
import ReactionFaceIcon from '@/components/ReactionFaceIcon.vue'
import { isBrowserOffline, isNetworkError } from '@/offline'

defineOptions({
  name: 'People',
})

const search = ref('')
const isAdmin = computed(() => isGameplanAdmin())

const orderByOptions = [
  { label: 'Name', value: 'full_name asc' },
  { label: 'Last updated', value: 'modified desc' },
  { label: 'Posts', value: 'posts' },
  { label: 'Replies', value: 'replies' },
  { label: 'Reactions received', value: 'reactions_received' },
] as const

type UiOrderBy = (typeof orderByOptions)[number]['value']

// `posts`/`replies`/`reactions_received` have no backing column - they're derived counts
// computed server-side per row - so those keep fetching at a steady `modified desc` and
// the sort below re-orders client-side. Only `full_name asc`/`modified desc` map to real
// columns and are sent straight through to `data/people.ts`'s shared list.
const orderBy = ref<UiOrderBy>('modified desc')
const derivedOrderBy = new Set(['posts', 'replies', 'reactions_received'])
watch(
  orderBy,
  (value) => {
    peopleOrderBy.value = derivedOrderBy.has(value) ? 'modified desc' : value
  },
  { immediate: true },
)

// Guests are excluded from the People page; `full_name`/`email` come from the users
// store (User.full_name/email), not GP User Profile's own copy - see PersonProfile.vue
// for why the store wins once it has a real (non-placeholder) record.
const profiles = computed(() => {
  return (people.data || [])
    .filter((profile) => useUser(profile.user).isNotGuest)
    .map((profile) => ({
      ...profile,
      email: useUser(profile.user).email,
      full_name: useUser(profile.user).full_name,
    }))
})

const peopleList = computed(() => {
  if (!profiles.value.length) return []

  if (search.value) {
    const term = search.value.toLowerCase()
    return profiles.value.filter(
      (profile) =>
        profile.full_name.toLowerCase().includes(term) ||
        profile.email.toLowerCase().includes(term),
    )
  }

  const sessionUser = useSessionUser()
  const myProfile = profiles.value.find((profile) => profile.user === sessionUser.name)
  let list = [myProfile, ...profiles.value.filter((profile) => profile !== myProfile)].filter(
    Boolean,
  ) as typeof profiles.value

  if (orderBy.value === 'posts') {
    list = [...list].sort((a, b) => b.discussions_count - a.discussions_count)
  } else if (orderBy.value === 'replies') {
    list = [...list].sort((a, b) => b.comments_count - a.comments_count)
  } else if (orderBy.value === 'reactions_received') {
    list = [...list].sort((a, b) => b.reactions_received - a.reactions_received)
  }
  return list
})

const listFailure = computed(() => {
  const failed = people.isFinished && !people.loading && people.error && people.data == null
  if (!failed) return null

  const offline = isBrowserOffline() || isNetworkError(people.error)
  return offline
    ? {
        title: "Can't load this while offline",
        message: 'The People list has not been saved for offline use yet.',
      }
    : {
        title: 'Could not load people',
        message: 'Something went wrong while loading this list. Retry to try again.',
      }
})

const isEmpty = computed(
  () => !people.loading && !listFailure.value && peopleList.value.length === 0,
)

usePageMeta(() => ({
  title: 'People',
}))
</script>
