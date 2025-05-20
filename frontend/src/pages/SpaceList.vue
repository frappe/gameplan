<template>
  <PageHeader>
    <Breadcrumbs class="h-7" :items="[{ label: 'Spaces', route: { name: 'Spaces' } }]" />
    <Button
      variant="solid"
      @click="
        () => {
          categoryForNewSpace = ''
          newSpaceDialog = true
        }
      "
    >
      <template #prefix><LucidePlus class="h-4 w-4" /></template>
      Add new
    </Button>
  </PageHeader>
  <NewSpaceDialog v-model="newSpaceDialog" :category="categoryForNewSpace" />
  <div class="mx-auto max-w-3xl px-2 sm:px-5 pb-20 sm:pb-80">
    <div class="px-2.5 mt-5 mb-3">
      <div
        class="py-2.5 px-3.5 flex gap-2.5 items-start text-ink-gray-8 rounded-md bg-surface-gray-1 border-outline-gray-1 text-p-base"
      >
        <svg
          class="w-4 h-5 shrink-0 text-gray-600"
          viewBox="0 0 16 16"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            fill-rule="evenodd"
            clip-rule="evenodd"
            d="M8 15C11.866 15 15 11.866 15 8C15 4.13401 11.866 1 8 1C4.13401 1 1 4.13401 1 8C1 11.866 4.13401 15 8 15ZM8 5.75C8.48325 5.75 8.875 5.35825 8.875 4.875C8.875 4.39175 8.48325 4 8 4C7.51675 4 7.125 4.39175 7.125 4.875C7.125 5.35825 7.51675 5.75 8 5.75ZM8 6.93604C8.27614 6.93604 8.5 7.15989 8.5 7.43604V11.1435C8.5 11.4196 8.27614 11.6435 8 11.6435C7.72386 11.6435 7.5 11.4196 7.5 11.1435V7.43604C7.5 7.15989 7.72386 6.93604 8 6.93604Z"
            fill="currentColor"
          />
        </svg>
        <p>
          Spaces keep discussions, tasks, and pages in one place. Use them to group by team, project
          or any topic. Spaces you join will show up on your sidebar.
        </p>
      </div>
    </div>
    <div class="mt-3 mb-3 flex px-2.5 items-center justify-between gap-2.5">
      <TextInput
        v-model="query"
        placeholder="Search"
        class="w-full"
        v-focus="!!!$route.query.teamId"
      >
        <template #prefix>
          <LucideSearch class="size-4 text-ink-gray-5" />
        </template>
      </TextInput>
      <TabButtons
        :buttons="[{ label: 'Public' }, { label: 'Private' }, { label: 'Archived' }]"
        v-model="currentTab"
      />
    </div>
    <div class="p-3" v-if="groupedSpaces.length === 0">
      <EmptyStateBox>
        <div class="text-ink-gray-5 text-base">No spaces</div>
      </EmptyStateBox>
    </div>
    <div>
      <div class="mt-12" v-for="group in groupedSpaces" :key="group.name">
        <div
          class="px-3 flex items-center gap-2 sticky top-12 py-2 bg-surface-white"
          :ref="(el) => (groupRefs[group.name] = el as HTMLElement)"
        >
          <div class="text-base text-ink-gray-8">
            {{ noCategories ? 'All spaces' : group.title || group.name }}
          </div>
          <Badge v-if="getCategoryUnreadCount(group.name) > 0">
            {{ getCategoryUnreadCount(group.name) }}
          </Badge>
          <DropdownMoreOptions
            class="ml-auto"
            placement="right"
            :options="categoryOptions(group)"
          />
        </div>
        <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 px-3">
          <router-link
            v-for="(d, index) in group.spaces"
            :key="d.name"
            class="rounded-md flex flex-col focus:outline-none focus-visible:ring-outline-gray-3 focus-visible:ring-2 justify-between border p-3 hover:bg-surface-gray-2 group transition-colors"
            :to="{
              name: 'Space',
              params: {
                spaceId: d.name,
              },
            }"
          >
            <div class="flex items-start w-full space-x-2">
              <div class="inline-flex">
                <span class="text-lg mr-1.5 font-[emoji] leading-5">
                  {{ d.icon }}
                </span>
                <span class="text-base leading-5 text-ink-gray-9 font-medium">
                  {{ d.title }}
                  <LucideLock
                    v-if="d.is_private"
                    class="h-3 w-3 text-ink-gray-6 inline ml-1 mb-0.5"
                  />
                </span>
              </div>
              <div class="!ml-auto flex">
                <Badge v-if="getSpaceUnreadCount(d.name) > 0" class="group-hover:bg-surface-white">
                  {{ getSpaceUnreadCount(d.name) }}
                </Badge>
              </div>
            </div>
            <div class="mt-2.5 flex items-center justify-between">
              <div>
                <span class="text-ink-gray-5 text-base" v-if="d.discussions_count ?? 0 > 0">
                  {{ d.discussions_count }}
                  {{ d.discussions_count == 1 ? 'post' : 'posts' }}
                </span>
              </div>

              <div class="flex items-center space-x-1" @click.prevent>
                <template v-if="!d.archived_at">
                  <Tooltip :text="'Leave space'" v-if="hasJoined(d.name)">
                    <Button
                      variant="ghost"
                      class="group-hover:opacity-100 sm:opacity-0 transition-opacity opacity-100"
                      @click="leaveSpace(d)"
                      :loading="isMethodLoading(d.name, 'leave')"
                    >
                      <template #icon>
                        <LucideUserRoundMinus class="size-4" />
                      </template>
                    </Button>
                  </Tooltip>
                  <Tooltip :text="'Join space'" v-else>
                    <Button
                      size="sm"
                      variant="ghost"
                      class="group-hover:opacity-100 sm:opacity-0 transition-opacity opacity-100"
                      @click="joinSpace(d)"
                      :loading="isMethodLoading(d.name, 'join')"
                    >
                      <template #icon>
                        <LucideUserRoundPlus class="h-4 w-4" />
                      </template>
                    </Button>
                  </Tooltip>
                  <SpaceOptions
                    class="group-hover:opacity-100 sm:opacity-0 transition-opacity opacity-100"
                    placement="right"
                    :spaceId="d.name"
                  />
                </template>
                <template v-else>
                  <Tooltip :text="'Unarchive space'">
                    <Button
                      size="sm"
                      @click="unarchiveSpace(d)"
                      variant="ghost"
                      class="group-hover:opacity-100 sm:opacity-0 transition-opacity opacity-100"
                    >
                      <template #icon>
                        <LucideArchiveRestore class="size-4" />
                      </template>
                    </Button>
                  </Tooltip>
                </template>
              </div>
            </div>
          </router-link>
        </div>
      </div>
    </div>
  </div>
  <Dialog :options="{ title: 'Change category title' }" v-model="editCategoryDialog.show">
    <template #body-content>
      <FormControl label="Title" v-model="editCategoryDialog.categoryTitle" v-focus:autoselect />
    </template>
    <template #actions>
      <div class="flex justify-end">
        <Button
          variant="solid"
          @click="
            () =>
              teams.setValue
                .submit({
                  name: editCategoryDialog.category.name,
                  title: editCategoryDialog.categoryTitle,
                })
                .then(() => {
                  editCategoryDialog.show = false
                  editCategoryDialog.category = null
                  editCategoryDialog.categoryTitle = ''
                })
          "
        >
          Submit
        </Button>
      </div>
    </template>
  </Dialog>
</template>
<script setup lang="ts">
import { onMounted, reactive, ref, nextTick } from 'vue'
import type { UnwrapRef } from 'vue'
import { Badge, Breadcrumbs, TabButtons, Button, Tooltip } from 'frappe-ui'
import { useDoctype } from 'frappe-ui/src/data-fetching'
import { noCategories, useGroupedSpaces } from '@/data/groupedSpaces'
import { hasJoined, joinedSpaces, getSpaceUnreadCount, unreadCount } from '@/data/spaces'
import NewSpaceDialog from '@/components/NewSpaceDialog.vue'
import SpaceOptions from '@/components/SpaceOptions.vue'
import PageHeader from '@/components/PageHeader.vue'
import DropdownMoreOptions from '@/components/DropdownMoreOptions.vue'
import { GPTeam, GPProject } from '@/types/doctypes'
import EmptyStateBox from '@/components/EmptyStateBox.vue'
import { useRoute } from 'vue-router'
import { scrollTo } from '@/utils/scrollContainer'
import { getScrollContainer } from '@/utils/scrollContainer'
import { createDialog } from '@/utils/dialogs'
import { vFocus } from '@/directives'

const teams = useDoctype<GPTeam>('GP Team')
const currentTab = ref('Public')
const categoryForNewSpace = ref('')
const query = ref('')
const groupRefs: Record<string, HTMLElement> = {}
const route = useRoute()

const groupedSpaces = useGroupedSpaces({
  filterFn: (space) =>
    Boolean(
      {
        Public: !space.archived_at,
        Private: space.is_private,
        Archived: space.archived_at,
      }[currentTab.value],
    ) && (query.value ? space.title.toLowerCase().includes(query.value.toLowerCase()) : true),
})

const newSpaceDialog = ref(false)
const editCategoryDialog = reactive({
  category: null,
  categoryTitle: '',
  show: false,
})

let spaces = useDoctype<GPProject>('GP Project')

onMounted(async () => {
  if (route.query.teamId) {
    await nextTick()
    setTimeout(() => {
      scrollToCategory(route.query.teamId as string)
    }, 100)
  }
})

function scrollToCategory(categoryId: string) {
  const scrollContainer = getScrollContainer()
  const element = groupRefs[categoryId]
  if (element) {
    const rect = element.getBoundingClientRect()
    const scrollTop = scrollContainer.scrollTop
    const offsetPosition = rect.top + scrollTop - 56
    scrollTo({ top: offsetPosition })
  }
}

function joinSpace(space) {
  spaces.runDocMethod
    .submit({
      method: 'join',
      name: space.name,
    })
    .then(joinedSpaces.reload)
}

function joinSpaces(spaceIds: string[]) {
  return spaces.runMethod
    .submit({
      method: 'join_spaces',
      params: {
        spaces: spaceIds,
      },
    })
    .then(joinedSpaces.reload)
}

function leaveSpace(space) {
  spaces.runDocMethod
    .submit({
      method: 'leave',
      name: space.name,
    })
    .then(joinedSpaces.reload)
}

function leaveSpaces(spaceIds: string[]) {
  return spaces.runMethod
    .submit({
      method: 'leave_spaces',
      params: {
        spaces: spaceIds,
      },
    })
    .then(joinedSpaces.reload)
}

function unarchiveSpace(space) {
  spaces.runDocMethod.submit({
    method: 'unarchive',
    name: space.name,
  })
}

function markAllAsRead(group) {
  const spaceIds = group.spaces.map((d) => d.name)
  createDialog({
    title: 'Mark all as read',
    message: `Are you sure you want to mark all discussions in ${group.title} as read? This action cannot be undone.`,
    actions: [
      {
        label: 'Mark all as read',
        variant: 'solid',
        onClick: ({ close }) => {
          return spaces.runMethod
            .submit({
              method: 'mark_all_as_read',
              params: {
                spaces: spaceIds,
              },
            })
            .then(() => {
              close()
              unreadCount.reload()
            })
        },
      },
    ],
  })
}

function isMethodLoading(docname, method) {
  return spaces.runDocMethod.isLoading(docname, method)
}

type GroupedSpaceItem = UnwrapRef<ReturnType<typeof useGroupedSpaces>>[number]

function categoryOptions(group: GroupedSpaceItem) {
  return [
    {
      label: 'Edit',
      condition: () => group.title !== 'Uncategorized',
      onClick: () => {
        editCategoryDialog.category = group
        editCategoryDialog.categoryTitle = group.title
        editCategoryDialog.show = true
      },
    },
    {
      label: 'Mark all as read',
      condition: () => group.title !== 'Uncategorized' && group.spaces.length > 0,
      onClick: () => markAllAsRead(group),
    },
    {
      label: 'Join all',
      onClick: () => joinSpaces(group.spaces.map((d) => d.name)),
    },
    {
      label: 'Leave all',
      onClick: () => leaveSpaces(group.spaces.map((d) => d.name)),
    },
    {
      label: 'New space',
      onClick: () => {
        if (group.title !== 'Uncategorized') {
          categoryForNewSpace.value = group.name
        }
        newSpaceDialog.value = true
      },
    },
  ]
}

function getCategoryUnreadCount(categoryId: string) {
  let count = 0
  for (const group of groupedSpaces.value) {
    if (group.name === categoryId) {
      for (const space of group.spaces) {
        count += getSpaceUnreadCount(space.name)
      }
    }
  }
  return count
}
</script>
