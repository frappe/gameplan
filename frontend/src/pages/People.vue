<template>
  <div class="flex h-full flex-col">
    <div class="flex flex-1">
      <div class="w-full">
        <PageHeaderMobile class="sm:hidden" title="People">
          <template #prefix>
            <PageHeaderBackButton :fallback-route="{ name: 'More' }" />
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
            <h2 class="text-2xl-semibold text-ink-gray-7">{{ peopleList.length }} members</h2>
            <div class="flex items-center gap-2">
              <Select
                class="shrink-0 !w-fit"
                align="end"
                :options="peopleSortOptions"
                v-model="sortField"
              />
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
                <ListHeaderCellSort
                  class="col-span-2"
                  :direction="directionFor('full_name')"
                  @click="sortPeopleBy('full_name')"
                >
                  Member
                  <template #sort-indicator><span /></template>
                </ListHeaderCellSort>
                <ListHeaderCellSort
                  align="end"
                  :direction="directionFor('discussions_count')"
                  @click="sortPeopleBy('discussions_count')"
                >
                  Posts
                  <template #sort-indicator><span /></template>
                </ListHeaderCellSort>
                <ListHeaderCellSort
                  align="end"
                  :direction="directionFor('comments_count')"
                  @click="sortPeopleBy('comments_count')"
                >
                  Replies
                  <template #sort-indicator><span /></template>
                </ListHeaderCellSort>
                <ListHeaderCellSort
                  align="end"
                  :direction="directionFor('reactions_received')"
                  @click="sortPeopleBy('reactions_received')"
                >
                  <template #prefix>
                    <ReactionFaceIcon class="size-4 text-ink-gray-5" aria-hidden="true" />
                  </template>
                  Received
                  <template #sort-indicator><span /></template>
                </ListHeaderCellSort>
                <ListHeaderCellSort
                  align="end"
                  :direction="directionFor('reactions_given')"
                  @click="sortPeopleBy('reactions_given')"
                >
                  <template #prefix>
                    <ReactionFaceIcon class="size-4 text-ink-gray-5" aria-hidden="true" />
                  </template>
                  Given
                  <template #sort-indicator><span /></template>
                </ListHeaderCellSort>
              </ListHeader>
              <ListRow
                v-for="user in peopleList"
                :key="user.name"
                :route="{
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
                :route="{
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

            <ErrorMessage class="mt-2" :message="people.error" />
            <EmptyStateBox v-if="isEmpty" class="mt-2">
              <span class="lucide-users mb-1 size-7 text-ink-gray-4" aria-hidden="true" />
              {{ search ? 'No members match your search' : 'No members yet' }}
            </EmptyStateBox>

            <div class="p-3" v-if="people.hasNextPage">
              <Button @click="people.next" :loading="people.loading"> Load more </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  PageHeaderBackButton,
  PageHeaderMobile,
  PageHeader,
  Breadcrumbs,
  Badge,
  Button,
  Select,
  TextInput,
  ErrorMessage,
  usePageMeta,
} from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCellSort, ListRow } from 'frappe-ui/list'
import { showSettingsDialog } from '@/components/Settings'
import { isGameplanAdmin, useSessionUser, useUser } from '@/data/users'
import {
  people,
  peopleSortDirection,
  peopleSortField,
  peopleSortOptions,
  sortPeopleBy,
  type PeopleSortField,
} from '@/data/people'
import EmptyStateBox from '@/components/EmptyStateBox.vue'
import UserAvatarWithHover from '@/components/UserAvatarWithHover.vue'
import ReactionFaceIcon from '@/components/ReactionFaceIcon.vue'

defineOptions({
  name: 'People',
})

const search = ref('')
const isAdmin = computed(() => isGameplanAdmin())

// Counts change between visits, and a failed load should not stick, so fetch on each visit.
people.reload()

// Guests are left out. Name and email come from the users store, the copy the rest of the
// app shows, so search matches it.
const profiles = computed(() => {
  return (people.data || [])
    .filter((profile) => useUser(profile.user).isNotGuest)
    .map((profile) => ({
      ...profile,
      email: useUser(profile.user).email,
      full_name: useUser(profile.user).full_name,
    }))
})

const sortField = computed({
  get: () => peopleSortField.value,
  set: (field: PeopleSortField | '') => {
    if (field) sortPeopleBy(field)
  },
})

function directionFor(field: PeopleSortField) {
  return peopleSortField.value === field ? peopleSortDirection.value : null
}

type Profile = (typeof profiles.value)[number]

function compareProfiles(a: Profile, b: Profile) {
  const field = peopleSortField.value
  let result = 0
  if (field === 'full_name' || field === 'modified') {
    result = a[field].localeCompare(b[field])
  } else {
    result = a[field] - b[field]
  }
  return peopleSortDirection.value === 'asc' ? result : -result
}

const peopleList = computed(() => {
  let list = profiles.value
  if (search.value) {
    const term = search.value.toLowerCase()
    list = list.filter(
      (profile) =>
        profile.full_name.toLowerCase().includes(term) ||
        profile.email.toLowerCase().includes(term),
    )
  }

  list = [...list].sort(compareProfiles)
  const myProfile = list.find((profile) => profile.user === useSessionUser().name)
  return myProfile ? [myProfile, ...list.filter((profile) => profile !== myProfile)] : list
})

const isEmpty = computed(() => !people.loading && !people.error && peopleList.value.length === 0)

usePageMeta(() => ({
  title: 'People',
}))
</script>
