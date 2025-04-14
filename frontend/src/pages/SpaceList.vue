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
    <div class="mt-3 mb-3 flex px-2.5">
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
    <div class="mb-8" v-for="group in groupedSpaces" :key="group.name">
      <div class="px-3 pb-2 flex items-center justify-between">
        <div class="text-ink-gray-8 text-base">
          {{ noCategories ? 'All spaces' : group.title || group.name }}
        </div>
        <DropdownMoreOptions
          placement="right"
          :options="[
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
                  categoryForNewSpace = group.name
                }
                newSpaceDialog = true
              },
            },
          ]"
        />
      </div>
      <div class="border-b mx-3"></div>
      <router-link
        v-for="(d, index) in group.spaces"
        :key="d.name"
        :to="{
          name: 'Space',
          params: {
            spaceId: d.name,
          },
        }"
        class="group relative block rounded-[10px] transition hover:bg-surface-gray-2"
      >
        <div class="flex h-full items-center space-x-4 overflow-hidden px-3 py-2">
          <span class="font-[emoji] text-2xl self-start mt-0.5">
            {{ d.icon }}
          </span>
          <div class="min-w-0 flex-1">
            <div class="flex min-w-0 items-center">
              <div class="overflow-hidden text-ellipsis whitespace-nowrap text-ink-gray-8">
                <span class="overflow-hidden text-ellipsis whitespace-nowrap text-base font-medium">
                  {{ d.title }}
                  <LucideLock
                    v-if="d.is_private"
                    class="h-3 w-3 text-ink-gray-6 inline ml-1 mb-0.5"
                  />
                </span>
              </div>
            </div>
            <div class="mt-1 flex min-w-0 items-center">
              <div
                class="overflow-hidden text-ellipsis whitespace-nowrap text-base text-ink-gray-5"
              >
                <span>
                  {{ d.discussions_count }}
                  {{ d.discussions_count == 1 ? 'post' : 'posts' }}
                </span>
              </div>
            </div>
          </div>
          <div class="ml-auto">
            <div class="flex items-center space-x-1" v-if="!d.archived_at" @click.prevent>
              <Button
                class="w-16"
                v-if="hasJoined(d.name)"
                @click="leaveSpace(d)"
                :loading="isMethodLoading(d.name, 'leave')"
              >
                Leave
              </Button>
              <Button
                class="w-16"
                v-else
                @click="joinSpace(d)"
                :loading="isMethodLoading(d.name, 'join')"
              >
                Join
              </Button>
              <SpaceOptions placement="right" :spaceId="d.name" />
            </div>
            <div v-else @click.prevent>
              <Button @click="unarchiveSpace(d)">Unarchive</Button>
            </div>
          </div>
        </div>
      </router-link>
    </div>
  </div>
  <Dialog :options="{ title: 'Change category title' }" v-model="editCategoryDialog.show">
    <template #body-content>
      <FormControl label="Title" v-model="editCategoryDialog.categoryTitle" />
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
import { reactive, ref } from 'vue'
import { Breadcrumbs, TabButtons } from 'frappe-ui'
import { useDoctype } from 'frappe-ui/src/data-fetching'
import { noCategories, useGroupedSpaces } from '@/data/groupedSpaces'
import { hasJoined, joinedSpaces } from '@/data/spaces'
import NewSpaceDialog from '@/components/NewSpaceDialog.vue'
import SpaceOptions from '@/components/SpaceOptions.vue'
import PageHeader from '@/components/PageHeader.vue'
import DropdownMoreOptions from '@/components/DropdownMoreOptions.vue'
import { GPProject } from '@/types/GPProject'
import { GPTeam } from '@/types/doctypes'
import LucideLock from '~icons/lucide/lock'
import EmptyStateBox from '@/components/EmptyStateBox.vue'

const teams = useDoctype<GPTeam>('GP Team')
const currentTab = ref('Public')
const categoryForNewSpace = ref('')

const groupedSpaces = useGroupedSpaces({
  filterFn: (space) =>
    Boolean(
      {
        Public: !space.archived_at,
        Private: space.is_private,
        Archived: space.archived_at,
      }[currentTab.value],
    ),
})

const newSpaceDialog = ref(false)
const editCategoryDialog = reactive({
  category: null,
  categoryTitle: '',
  show: false,
})

let spaces = useDoctype<GPProject>('GP Project')

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

function isMethodLoading(docname, method) {
  return spaces.runDocMethod.isLoading(docname, method)
}
</script>
