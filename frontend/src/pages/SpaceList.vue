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
    <div class="mt-5 flex px-2.5">
      <TabButtons :buttons="[{ label: 'Active' }, { label: 'Archived' }]" v-model="currentTab" />
    </div>
    <div v-for="group in groupedSpaces" :key="group.name">
      <div class="p-3 pt-8 flex items-center justify-between">
        <div class="text-ink-gray-9 text-base">{{ group.title || group.name }}</div>
        <DropdownMoreOptions
          placement="right"
          :options="[
            {
              label: 'Edit',
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
                categoryForNewSpace = group.name
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
              <div class="overflow-hidden text-ellipsis whitespace-nowrap text-ink-gray-9">
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
import { useGroupedSpaces } from '@/data/groupedSpaces'
import { hasJoined, joinedSpaces } from '@/data/spaces'
import NewSpaceDialog from '@/components/NewSpaceDialog.vue'
import SpaceOptions from '@/components/SpaceOptions.vue'
import PageHeader from '@/components/PageHeader.vue'
import DropdownMoreOptions from '@/components/DropdownMoreOptions.vue'
import { GPProject } from '@/types/GPProject'
import { GPTeam } from '@/types/doctypes'
import LucideLock from '~icons/lucide/lock'

const teams = useDoctype<GPTeam>('GP Team')
const currentTab = ref('Active')
const categoryForNewSpace = ref('')

const groupedSpaces = useGroupedSpaces({
  filterFn: (space) =>
    Boolean(currentTab.value == 'Active' ? !space.archived_at : space.archived_at),
})

const newSpaceDialog = ref(false)
const editCategoryDialog = reactive({
  category: null,
  categoryTitle: '',
  show: false,
})

let spaces = useDoctype<GPProject>('GP Project')
// spaces.runMethod.submit({})

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
